# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger         import Logger

#--------------
# local imports
# -------------

from .utils import Table, fromJSON, UNKNOWN, EXPIRED, CURRENT, INFINITE_TIME, TSTAMP_FORMAT
from ..error import ReadingKeyError, ReadingTypeError

# ----------------
# Module Constants
# ----------------

# No pre-registerd instruments by default
DEFAULT_INSTRUMENT = []

# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')


# ------------------------
# Module Utility Functions
# ------------------------

def _populateRepl(transaction, rows):
    '''Dimension initial data loading (replace flavour)'''
    transaction.executemany(
        '''INSERT OR REPLACE INTO instrument_t (
            instrument_id,
            name,
            mac_address,
            calibration_k,
            calibrated_since,
            calibrated_until,
            calibrated_state,
            current_loc_id
        ) VALUES(
            :instrument_id,
            :name,
            :mac_address,
            :calibration_k,
            :calibrated_since,
            :calibrated_until,
            :calibrated_state,
            :current_loc_id
        )
        ''', rows)

        
def _populateIgn(transaction, rows):
    '''Dimension initial data loading (ignore flavour)'''
    transaction.executemany(
        '''INSERT OR IGNORE INTO instrument_t (
            instrument_id,
            name,
            mac_address,
            calibration_k,
            calibrated_since,
            calibrated_until,
            calibrated_state,
            current_loc_id
        ) VALUES(
            :instrument_id,
            :name,
            :mac_address,
            :calibration_k,
            :calibrated_since,
            :calibrated_until,
            :calibrated_state,
            :current_loc_id
        )
        ''', rows)

def _updateCalibration(cursor, row):
    '''
    Updates Instrument calibration constant keeping its history
    row is a dictionary with at least the following keys: 'name', 'mac', 'calib'
    Returns a Deferred.
    '''
    row['eff_date']      = datetime.datetime.utcnow().strftime(TSTAMP_FORMAT)
    row['exp_date']      = INFINITE_TIME
    row['calib_expired'] = EXPIRED
    row['calib_flag']    = CURRENT

    cursor.execute(
        '''
        UPDATE instrument_t SET calibrated_until = :eff_date, calibrated_state = :calib_expired
        WHERE mac_address == :mac AND calibrated_state == :calib_flag
        ''', row)
    cursor.execute(
        '''
        INSERT INTO instrument_t (
            name,
            mac_address, 
            calibration_k,
            calibrated_since,
            calibrated_until,
            calibrated_state
        ) VALUES (
            :name,
            :mac,
            :calib,
            :eff_date,
            :exp_date,
            :calib_flag
        )
        ''',  row)

# ============================================================================ #
#                               INSTRUMENT TABLE (DIMENSION)
# ============================================================================ #

class Instrument(Table):

    FILE = 'instruments.json'

    def __init__(self, pool, validate=False):
        Table.__init__(self, pool)

    def table(self):
        '''
        Create the SQLite Units table.
        Returns a Deferred
        '''
        log.info("Creating instrument_t Table if not exists")
        return self.pool.runOperation(
            '''
            CREATE TABLE IF NOT EXISTS instrument_t
            (
            instrument_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT,
            mac_address        TEXT, 
            calibration_k      REAL,
            calibrated_since   TEXT,
            calibrated_until   TEXT,
            calibrated_state   TEXT,
            current_loc_id     INTEGER NOT NULL DEFAULT -1 REFERENCES location_t(location_id)
            );
            '''
        )


    def populate(self, replace):
        '''
        Populate the SQLite Instruments Table.
        Returns a Deferred
        '''
        if replace:
            log.info("Replacing Instruments Table data")
            return self.pool.runInteraction( _populateRepl, self.rows() )
        else:
            log.info("Populating Instruments Table if empty")
            return self.pool.runInteraction( _populateIgn, self.rows() )

    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject in SQLite APIfor schema generation'''
        return fromJSON( os.path.join(self.json_dir, Instrument.FILE), DEFAULT_INSTRUMENT)


    # =======
    # OPERATIONAL API
    # =======

    # -----------------------
    # Instrument registration
    # -----------------------

    @inlineCallbacks
    def register(self, row):
        '''
        Registers an instrument given its MAC address, friendly name and calibration constant
        '''
        log.info("Instrument registration request => name: {name} mac: {mac}", name=row['name'], mac=row['mac'])

        instrument = yield self.findMAC(row)
        
        # if  instrument with that MAC already exists, may be update it ...
        if len(instrument):
            instrument = instrument[0]  # Keep only the first row
            log.info("Instrument with the same MAC already registered")
            # If the new name is not equal to the old one, change it
            if row['name']  != instrument[0]:
            # unless the new name is already being used by another instrument
                instrument2 = yield self.findName(row)
                if not len(instrument2):
                    log.info("Changing instrument name to {name}", name=row['name'])
                    yield self.updateName(row)
            # If the new calibration constant is not equal to the old one, change it
            if row['calib'] != instrument[2]:
                log.info("Changing instrument calibration data to {calib}", calib=row['calib'])
                yield self.updateCalibration(row)   
        else:
            # Find other posible existing instruments with the same name
            # We require the names to be unique as well.
            # If that condition is met, we add a new instrument
            instrument = yield self.findName(row)
            if len(instrument):
                log.info("Another instrument already registered with the same name: {name}", name=row['name']) 
            else:
                yield self.addNew(row)
                log.info("Brand new instrument registered: {name}", name=row['name']) 




    def findMAC(self, row):
        '''
        Look up instrument parameters given its MAC address
        row is a dictionary with at least the following keys: 'mac'
        Returns a Deferred.
        '''
        row['calib_flag'] = CURRENT
        return self.pool.runQuery(
            '''
            SELECT name, mac_address, calibration_k 
            FROM instrument_t 
            WHERE mac_address == :mac
            AND calibrated_state == :calib_flag
            ''', row)


    def findName(self, row):
        '''
        Look up instrument parameters given its name
        row is a dictionary with at least the following keys: 'name'
        Returns a Deferred.
        '''
        row['calib_flag'] = CURRENT
        return self.pool.runQuery(
            '''
            SELECT instrument_id, mac_address, calibration_k, current_loc_id 
            FROM instrument_t 
            WHERE name == :name
            AND calibrated_state == :calib_flag 
            ''', row)



    def addNew(self, row):
        '''
        Adds a brand new instrument given its registration parameters.
        row is a dictionary with the following keys: 'name', 'mac', 'calib'
        Returns a Deferred.
        '''
        row['eff_date']   = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row['exp_date']   = INFINITE_TIME
        row['calib_flag'] = CURRENT
        return self.pool.runOperation( 
            '''
            INSERT INTO instrument_t (
                name,
                mac_address,
                calibration_k,
                calibrated_since,
                calibrated_until,
                calibrated_state
            ) VALUES (
                :name,
                :mac,
                :calib,
                :eff_date,
                :exp_date,
                :calib_flag
            )
            ''', row)

   
    def updateName(self, row):
        '''
        Changes all instrument name records with the same MAC
        row is a dictionary with at least the following keys: 'mac' , 'name'
        Returns a Deferred.
        '''
        return self.pool.runOperation( 
            '''
            UPDATE instrument_t SET name=:name
            WHERE mac_address == :mac 
            ''', row)


    def updateLocation(self, row):
        '''
        Changes all instrument location records with the same MAC
        row is a dictionary with at least the following keys: 'mac' , 'loc_id'
        Returns a Deferred.
        '''
        return self.pool.runOperation( 
            '''
            UPDATE instrument_t SET current_loc_id=:loc_id
            WHERE mac_address == :mac 
            ''', row )


    def updateCalibration(self, row):
        '''Updates Instrument calibration constant keeping its history'''
        return self.pool.runInteraction( _updateCalibration, row )
      