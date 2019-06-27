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

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.logger         import Logger

#--------------
# local imports
# -------------


from tessdb.sqlite3.utils import Table, fromJSON, START_TIME, INFINITE_TIME, CURRENT

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
        "signal_strength_units"     : "dBm",
        "valid_since"               : START_TIME,
        "valid_until"               : INFINITE_TIME,
        "valid_state"               : CURRENT,
        "timestamp_source"          : "Subscriber",
        "reading_source"            : "Direct"
    },
    {
        "units_id"                  : 1, 
        "frequency_units"           : "Hz",
        "magnitude_units"           : "Mv/arcsec^2",
        "ambient_temperature_units" : "deg. C",
        "sky_temperature_units"     : "deg. C",
        "azimuth_units"             : "degrees",
        "altitude_units"            : "degrees",
        "longitude_units"           : "degrees",
        "latitude_units"            : "degrees",
        "height_units"              : "m",
        "signal_strength_units"     : "dBm",
        "valid_since"               : START_TIME,
        "valid_until"               : INFINITE_TIME,
        "valid_state"               : CURRENT,
        "timestamp_source"          : "Publisher",
        "reading_source"            : "Direct"
    },
    {  
        "units_id"                  : 2, 
        "frequency_units"           : "Hz",
        "magnitude_units"           : "Mv/arcsec^2",
        "ambient_temperature_units" : "deg. C",
        "sky_temperature_units"     : "deg. C",
        "azimuth_units"             : "degrees",
        "altitude_units"            : "degrees",
        "longitude_units"           : "degrees",
        "latitude_units"            : "degrees",
        "height_units"              : "m",
        "signal_strength_units"     : "dBm",
        "valid_since"               : START_TIME,
        "valid_until"               : INFINITE_TIME,
        "valid_state"               : CURRENT,
        "timestamp_source"          : "Subscriber",
        "reading_source"            : "Imported"
    },
    {
        "units_id"                  : 3, 
        "frequency_units"           : "Hz",
        "magnitude_units"           : "Mv/arcsec^2",
        "ambient_temperature_units" : "deg. C",
        "sky_temperature_units"     : "deg. C",
        "azimuth_units"             : "degrees",
        "altitude_units"            : "degrees",
        "longitude_units"           : "degrees",
        "latitude_units"            : "degrees",
        "height_units"              : "m",
        "signal_strength_units"     : "dBm",
        "valid_since"               : START_TIME,
        "valid_until"               : INFINITE_TIME,
        "valid_state"               : CURRENT,
        "timestamp_source"          : "Publisher",
        "reading_source"            : "Imported"
    }
]


# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------


# ============================================================================ #
#                               UNITS TABLE (DIMENSION)
# ============================================================================ #

class TESSUnits(Table):

    FILE = 'tess_units.json'
    
    def __init__(self, connection):
        '''Create and populate the SQLite Units Table'''
        Table.__init__(self, connection)
        # Cached row ids
        self._id = {}
        self._id['Publisher']  = None
        self._id['Subscriber'] = None


    def table(self):
        '''
        Create the SQLite Units table.
        '''
        log.info("Creating tess_units_t Table if not exists")
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS tess_units_t
            (
            units_id                  INTEGER PRIMARY KEY AUTOINCREMENT, 
            frequency_units           TEXT,
            magnitude_units           TEXT,
            ambient_temperature_units TEXT,
            sky_temperature_units     TEXT,
            azimuth_units             TEXT,
            altitude_units            TEXT,
            longitude_units           TEXT,
            latitude_units            TEXT,
            height_units              TEXT,
            signal_strength_units     TEXT,
            timestamp_source          TEXT,
            reading_source            TEXT,
            valid_since               TEXT,
            valid_until               TEXT,
            valid_state               TEXT
            );
            '''
        )
        self.connection.commit()


    def populate(self, json_dir):
        '''
        Populate the SQLite Units Table.
        '''
        read_rows = self.rows(json_dir)
        log.info("Populating/Replacing Units Table data")
        self.connection.executemany(
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
                signal_strength_units,
                timestamp_source,
                reading_source,
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
                :signal_strength_units,
                :timestamp_source,
                :reading_source,
                :valid_since,
                :valid_until,
                :valid_state
            )'''
            , read_rows 
        )
        self.connection.commit()
      
    
    # --------------
    # Helper methods
    # --------------

    def rows(self, json_dir):
        '''Generate a list of rows to inject in SQLite API'''
        read_rows = fromJSON(os.path.join(json_dir, TESSUnits.FILE), DEFAULT_UNITS)
        return read_rows

   # ================
   # OPERATIONAL API
   # ================


    @inlineCallbacks
    def latest(self, timestamp_source="Subscriber", reading_source="Direct"):

        def queryLatest(dbpool, timestamp_source):
            row = {
                'valid_state'     : CURRENT, 
                'timestamp_source': timestamp_source,  
                'reading_source'  : reading_source
            }
            return dbpool.runQuery(
            '''
            SELECT units_id FROM tess_units_t 
            WHERE valid_state == :valid_state 
            AND timestamp_source == :timestamp_source
            AND reading_source == :reading_source
            ''', row)

        if self._id.get(timestamp_source) is None:
            row = yield queryLatest(self.pool, timestamp_source)
            self._id[timestamp_source] = row[0][0]
        returnValue(self._id[timestamp_source])
   
