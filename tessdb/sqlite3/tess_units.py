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
from twisted.internet.threads import deferToThread
from twisted.logger         import Logger

#--------------
# local imports
# -------------

# -- beware of absolute_import in Python 3 when doing import utils
import utils
from .utils import Table, fromJSON

# ----------------
# Module Constants
# ----------------

# Default Units data if no JSON file is present
DEFAULT_UNITS = {  
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
    "valid_since"               : utils.START_TIME,
    "valid_until"               : utils.INFINITE_TIME,
    "valid_state"               : utils.CURRENT,
    "timestamp_source"          : "Subscriber"
}


# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------

def _populate(transaction, rows):
    '''Dimension initial data loading (replace flavour)'''
    transaction.executemany(
        '''INSERT OR REPLACE INTO tess_units_t (
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
            valid_state,
            timestamp_source
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
            :valid_state,
            :timestamp_source
        )''', rows)



# ============================================================================ #
#                               UNITS TABLE (DIMENSION)
# ============================================================================ #

class TESSUnits(Table):

    FILE = 'tess_units.json'
    
    def __init__(self, pool):
        '''Create and populate the SQLite Units Table'''
        Table.__init__(self, pool)
        # Cached row ids
        self._id = {}
        self._id['Publisher']  = None
        self._id['Subscriber'] = None


    def table(self):
        '''
        Create the SQLite Units table.
        Returns a Deferred
        '''
        log.info("Creating tess_units_t Table if not exists")
        return self.pool.runOperation(
            '''
            CREATE TABLE IF NOT EXISTS tess_units_t
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
            valid_state               TEXT,
            timestamp_source          TEXT
            );
            '''
        )


    @inlineCallbacks
    def populate(self, json_dir):
        '''
        Populate the SQLite Units Table.
        Returns a Deferred
        '''
        
        read_rows = yield self.rows(json_dir)
        log.info("Populating/Replacing Units Table data")
        yield self.pool.runInteraction( _populate, read_rows )
      
    
    # --------------
    # Helper methods
    # --------------

    @inlineCallbacks
    def rows(self, json_dir):
        '''Generate a list of rows to inject in SQLite API'''
        read_rows = yield deferToThread(fromJSON, os.path.join(json_dir, TESSUnits.FILE), [DEFAULT_UNITS])
        returnValue(read_rows)

   # ================
   # OPERATIONAL API
   # ================


    @inlineCallbacks
    def latest(self, timestamp_source="Subscriber"):

        def queryLatest(dbpool, timestamp_source):
            row = {'valid_state': utils.CURRENT, 'timestamp_source': timestamp_source }
            return dbpool.runQuery(
            '''
            SELECT units_id FROM tess_units_t 
            WHERE valid_state == :valid_state 
            AND timestamp_source == :timestamp_source
            ''', row)

        if self._id[timestamp_source] is None:
            row = yield queryLatest(self.pool, timestamp_source)
            self._id[timestamp_source] = row[0][0]
        returnValue(self._id[timestamp_source])
   