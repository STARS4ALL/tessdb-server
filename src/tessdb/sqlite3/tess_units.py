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


from tessdb.sqlite3.utils import Table, START_TIME, INFINITE_TIME, CURRENT

# ----------------
# Module Constants
# ----------------

# Default Units data if no JSON file is present
DEFAULT_UNITS = [
    {  
        "units_id"                  : 0, 
        "timestamp_source"          : "Subscriber",
        "reading_source"            : "Direct"
    },
    {
        "units_id"                  : 1, 
        "timestamp_source"          : "Publisher",
        "reading_source"            : "Direct"
    },
    {  
        "units_id"                  : 2,
        "timestamp_source"          : "Subscriber",
        "reading_source"            : "Imported"
    },
    {
        "units_id"                  : 3, 
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
            timestamp_source          TEXT,
            reading_source            TEXT
            );
            '''
        )
        self.connection.commit()


    def populate(self):
        '''
        Populate the SQLite Units Table.
        '''
        read_rows = self.rows()
        log.info("Populating/Replacing Units Table data with default values")
        self.connection.executemany(
            '''INSERT OR REPLACE INTO tess_units_t (
                units_id,   
                timestamp_source,
                reading_source
            ) VALUES (
                :units_id,
                :timestamp_source,
                :reading_source
            )''', read_rows )
        self.connection.commit()
      
    
    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject in SQLite API'''
        return DEFAULT_UNITS

   # ================
   # OPERATIONAL API
   # ================


    @inlineCallbacks
    def latest(self, timestamp_source="Subscriber", reading_source="Direct"):

        def queryLatest(dbpool, timestamp_source):
            row = {
                'timestamp_source': timestamp_source,  
                'reading_source'  : reading_source
            }
            return dbpool.runQuery(
                '''
                SELECT units_id FROM tess_units_t
                WHERE timestamp_source == :timestamp_source
                AND reading_source == :reading_source
                ''', row)

        if self._id.get(timestamp_source) is None:
            row = yield queryLatest(self.pool, timestamp_source)
            self._id[timestamp_source] = row[0][0]
        returnValue(self._id[timestamp_source])
   
