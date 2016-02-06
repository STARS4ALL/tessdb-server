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

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger         import Logger

#--------------
# local imports
# -------------

from .utils import Table, fromJSON, UNKNOWN, CURRENT

# ----------------
# Module Constants
# ----------------

# Default Units data if no JSON file is present
DEFAULT_UNITS = [
     {  
    "units_id"                  : 0, 
    "frequency_units"           : "Hz",
    "magnitude_units"           : "Mv/arcsec^2",
    "ambient_temperature_units" : "deg. C",
    "sky_temperature_units"     : "deg. C",
    "azimuth_units"             : "degrees",
    "altitude_units"            : "degrees",
    "longitude_units"           : "degrees",
    "latitude_units"            : "degrees",
    "height_units"              : "m",
    "valid_since"               : "2016-01-01 00:00:00",
    "valid_until"               : "2999-12-31 23:59:59",
    "valid_state"               : "Current"
    }
]

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
        '''INSERT OR REPLACE INTO units_t (
            units_id,
            frequency_units,
            magnitude_units,
            ambient_temperature_units,
            sky_temperature_units,
            azimuth_units,
            altitude_units,
            longitude_units,
            latitude_units,
            height_units,
            valid_since,
            valid_until,
            valid_state
        ) VALUES (
            :units_id,
            :frequency_units,
            :magnitude_units,
            :ambient_temperature_units,
            :sky_temperature_units,
            :azimuth_units,
            :altitude_units,
            :longitude_units,
            :latitude_units,
            :height_units,
            :valid_since,
            :valid_until,
            :valid_state
        )''', rows)

        
def _populateIgn(transaction, rows):
    '''Dimension initial data loading (ignore flavour)'''
    transaction.executemany(
    '''INSERT OR IGNORE INTO units_t (
            units_id,
            frequency_units,
            magnitude_units,
            ambient_temperature_units,
            sky_temperature_units,
            azimuth_units,
            altitude_units,
            longitude_units,
            latitude_units,
            height_units,
            valid_since,
            valid_until,
            valid_state
        ) VALUES (
            :units_id,
            :frequency_units,
            :magnitude_units,
            :ambient_temperature_units,
            :sky_temperature_units,
            :azimuth_units,
            :altitude_units,
            :longitude_units,
            :latitude_units,
             :height_units,
            :valid_since,
            :valid_until,
            :valid_state
        )''', rows)

        


# ============================================================================ #
#                               UNITS TABLE (DIMENSION)
# ============================================================================ #

class Units(Table):

    FILE = 'units.json'
    
    def __init__(self, pool):
        '''Create and populate the SQLite Units Table'''
        Table.__init__(self, pool)
        self.id = None


    def table(self):
        '''
        Create the SQLite Units table.
        Returns a Deferred
        '''
        log.info("Creating units_t Table if not exists")
        return self.pool.runOperation(
            '''
            CREATE TABLE IF NOT EXISTS units_t
            (
            units_id                  INTEGER PRIMARY KEY AUTOINCREMENT, 
            frequency_units           REAL,
            magnitude_units           REAL,
            ambient_temperature_units REAL,
            sky_temperature_units     REAL,
            azimuth_units             REAL,
            altitude_units            REAL,
            longitude_units           REAL,
            latitude_units            REAL,
            height_units              REAL,
            valid_since               TEXT,
            valid_until               TEXT,
            valid_state               TEXT
            );
            '''
        )


    def populate(self, replace):
        '''
        Populate the SQLite Units Table.
        Returns a Deferred
        '''
        
        
        if replace:
            log.info("Replacing Units Table data")
            return self.pool.runInteraction( _populateRepl, self.rows() )
        else:
            log.info("Populating Units Table if empty")
            return self.pool.runInteraction( _populateIgn, self.rows() )


    
    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject in SQLite API'''
        return fromJSON( os.path.join(self.json_dir, Units.FILE), DEFAULT_UNITS)

   # ================
   # OPERATIONAL API
   # ================


    @inlineCallbacks
    def latest(self):

        def queryLatest(dbpool):
            row = {'valid_state': CURRENT }
            return dbpool.runQuery(
            '''
            SELECT units_id FROM units_t WHERE valid_state == :valid_state
            ''', row)

        if self.id is None:
            row = yield queryLatest(self.pool)
            self.id = row[0][0]
        returnValue(self.id)
   