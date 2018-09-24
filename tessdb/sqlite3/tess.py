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

from __future__ import division, absolute_import

import os
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.logger         import Logger

#--------------
# local imports
# -------------

from tessdb.sqlite3.utils import Table, fromJSON, TSTAMP_FORMAT, INFINITE_TIME, EXPIRED, CURRENT
from tessdb.error import ReadingKeyError, ReadingTypeError

# ----------------
# Module Constants
# ----------------

# No pre-registerd instruments by default
DEFAULT_INSTRUMENT = []

# No predefined deployment of TESS instruments to Loacations
DEFAULT_DEPLOYMENT = []

# -----------------------
# Module Global Variables
# -----------------------

log  = Logger(namespace='dbase')
log2 = Logger(namespace='registry')


# ------------------------
# Module Utility Functions
# ------------------------

def _updateCalibration(cursor, row):
    '''
    Updates Instrument calibration constant keeping its history
    row is a dictionary with at least the following keys: 'name', 'mac', 'calib'
    Returns a Deferred.
    '''
    row['eff_date']      = datetime.datetime.utcnow().strftime(TSTAMP_FORMAT)
    row['exp_date']      = INFINITE_TIME
    row['valid_expired'] = EXPIRED
    row['valid_flag']    = CURRENT

    cursor.execute(
        '''
        UPDATE tess_t SET valid_until = :eff_date, valid_state = :valid_expired
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)
    cursor.execute(
        '''
        INSERT INTO tess_t (
            name,
            mac_address, 
            zero_point,
            valid_since,
            valid_until,
            valid_state,
            location_id
        ) VALUES (
            :name,
            :mac,
            :calib,
            :eff_date,
            :exp_date,
            :valid_flag,
            :location
        )
        ''',  row)



# ============================================================================ #
#                              TESS INSTRUMENT TABLE (DIMENSION)
# ============================================================================ #

class TESS(Table):

    DEPL_FILE        = 'tess_location.json'
    INSTRUMENTS_FILE = 'tess.json'

    def __init__(self, connection, validate=False):
        Table.__init__(self, connection)
        self.resetCounters()

    def table(self):
        '''
        Create the SQLite Units table.
        '''
        log.info("Creating tess_t Table if not exists")
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS tess_t
            (
            tess_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT,
            mac_address   TEXT, 
            zero_point    REAL,
            filter        TEXT DEFAULT 'UVIR',
            valid_since   TEXT,
            valid_until   TEXT,
            valid_state   TEXT,
            location_id   INTEGER NOT NULL DEFAULT -1 REFERENCES location_t(location_id),
            model         TEXT    DEFAULT 'TESS-W',
            firmware      TEXT    DEFAULT '1.0',
            channel       INTEGER DEFAULT 0,
            cover_offset  REAL    DEFAULT 0.0,
            fov           REAL    DEFAULT 17.0,
            azimuth       REAL    DEFAULT 0.0,
            altitude      REAL    DEFAULT 90.0
            );
            '''
        ).commit()

    def indices(self):
        '''
        Create indices to SQLite Units table.
        '''
        log.info("Creating tess_t Indexes if not exists")
        cursor = self.connection.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS tess_name_i ON tess_t(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS tess_mac_i ON tess_t(mac_address);")
        cursor.commit()


    def views(self):
        '''
        Create Views associated to this dimension.
        '''
        log.info("Creating tess_t Views if not exists")
        self.connection.execute(
            '''
            CREATE VIEW IF NOT EXISTS tess_v 
            AS SELECT
                tess_t.tess_id,
                tess_t.name,
                tess_t.channel,
                tess_t.model,
                tess_t.firmware,
                tess_t.mac_address,
                tess_t.zero_point,
                tess_t.cover_offset,
                tess_t.filter,
                tess_t.fov,
                tess_t.azimuth,
                tess_t.altitude,
                tess_t.valid_since,
                tess_t.valid_until,
                tess_t.valid_state,
                location_t.contact_person,
                location_t.organization,
                location_t.contact_email,
                location_t.site,
                location_t.longitude,
                location_t.latitude,
                location_t.elevation,
                location_t.zipcode,
                location_t.location,
                location_t.province,
                location_t.country,
                location_t.timezone
            FROM tess_t JOIN location_t USING (location_id);
            '''
        ).commit()


    def populate(self, json_dir):
        '''
        Populate the SQLite Instruments Table.
        '''
        if os.path.exists(os.path.join(json_dir, TESS.INSTRUMENTS_FILE)):
            log.info("Loading instruments file")
            read_rows = fromJSON(os.path.join(json_dir, TESS.INSTRUMENTS_FILE), DEFAULT_INSTRUMENT)
            self.connection.executemany(
                '''INSERT OR REPLACE INTO tess_t (
                    tess_id,
                    name,
                    mac_address,
                    zero_point,
                    filter,
                    valid_since,
                    valid_until,
                    valid_state,
                    location_id
                ) VALUES (
                    :tess_id,
                    :name,
                    :mac_address,
                    :zero_point,
                    :filter,
                    :valid_since,
                    :valid_until,
                    :valid_state,
                    :location_id
                )
                '''
                , read_rows).commit()

        log.info("Assigning locations to instruments")
        read_rows = fromJSON(os.path.join(json_dir, TESS.DEPL_FILE), DEFAULT_DEPLOYMENT)
        self.connection.executemany( 
            '''UPDATE tess_t SET location_id = (
                SELECT location_id FROM location_t
                    WHERE  location_t.site == :site
                )
                WHERE name == :name
            '''
            , read_rows ).commit()


    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.nregister = 0
        self.nCreation = 0
        self.nUpdNameChange  = 0
        self.nUpdCalibChange = 0 
        self.rejUpdDupName   = 0
        self.rejCreaDupName  = 0 
    

    def getCounters(self):
        '''get stat counters'''
        return [ 
                self.nregister, 
                self.nCreation,
                self.nUpdNameChange, 
                self.nUpdCalibChange, 
                self.rejUpdDupName,
                self.rejCreaDupName, 
                ]

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
        Returns a Deferred.
        '''
        log2.debug("New registration request for {row}", row=row)
        self.nregister += 1
        instrument = yield self.findMAC(row)
        # if  instrument with that MAC already exists, may be update it ...
        if len(instrument):
            instrument = instrument[0]  # Keep only the first row
            # If the new name is not equal to the old one, change it
            if row['name']  != instrument[0]:
            # unless the new name is already being used by another instrument
                instrument2 = yield self.findName(row)
                if not len(instrument2):
                    self.nUpdNameChange += 1
                    yield self.updateName(row)
                    log2.info("Changed instrument name to {name}", name=row['name'])
                else:
                    self.rejUpdDupName += 1
                    log2.info("Rejected: existing instrument name {name} modification due to other instrument using the same name",name=row['name'])

            # If the new calibration constant is not equal to the old one, change it
            if row['calib'] != instrument[2]:
                row['location'] = instrument[3] # carries over the location id
                yield self.updateCalibration(row)
                self.nUpdCalibChange += 1
                log2.info("{name} Changed instrument calibration data to {calib}", name=row['name'], calib=row['calib'])
        else:
            # Find other posible existing instruments with the same name
            # We require the names to be unique.
            # If that condition is met, we add a new instrument
            instrument = yield self.findName(row) 
            if len(instrument):
                existing_mac = instrument[0][1]
                log2.info("Registration rejected for new MAC {mac}: another instrument already registered with the same name: {name} and MAC: {existing_mac}", 
                    name=row['name'], mac=row['mac'], existing_mac=existing_mac) 
                self.rejCreaDupName += 1
            else:
                yield self.addNew(row)
                self.nCreation += 1
                log.info("Brand new instrument registered: {name}", name=row['name'])
        


    def findMAC(self, row):
        '''
        Look up instrument parameters given its MAC address
        row is a dictionary with at least the following keys: 'mac'
        Returns a Deferred.
        '''
        row['valid_flag'] = CURRENT
        return self.pool.runQuery(
            '''
            SELECT name, mac_address, zero_point, location_id, filter 
            FROM tess_t 
            WHERE mac_address == :mac
            AND valid_state == :valid_flag
            ''', row)


    def findName(self, row):
        '''
        Look up instrument parameters given its name
        row is a dictionary with at least the following keys: 'name'
        Returns a Deferred.
        '''
        row['valid_flag'] = CURRENT
        return self.pool.runQuery(
            '''
            SELECT tess_id, mac_address, zero_point, location_id, filter 
            FROM tess_t 
            WHERE name == :name
            AND valid_state == :valid_flag 
            ''', row)



    def addNew(self, row):
        '''
        Adds a brand new instrument given its registration parameters.
        row is a dictionary with the following keys: 'name', 'mac', 'calib'
        Returns a Deferred.
        '''
        row['eff_date']   = datetime.datetime.utcnow().strftime(TSTAMP_FORMAT)
        row['exp_date']   = INFINITE_TIME
        row['valid_flag'] = CURRENT
        return self.pool.runOperation( 
            '''
            INSERT INTO tess_t (
                name,
                mac_address,
                zero_point,
                valid_since,
                valid_until,
                valid_state
            ) VALUES (
                :name,
                :mac,
                :calib,
                :eff_date,
                :exp_date,
                :valid_flag
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
            UPDATE tess_t SET name=:name
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
            UPDATE tess_t SET location_id=:loc_id
            WHERE mac_address == :mac 
            ''', row )


    def updateCalibration(self, row):
        '''Updates Instrument calibration constant keeping its history'''
        return self.pool.runInteraction( _updateCalibration, row )
      