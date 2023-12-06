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

import sqlite3

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks
from twisted.logger         import Logger

#--------------
# local imports
# -------------

from . import NAMESPACE
from .utils import roundDateTime

from tessdb.logger import setLogLevel
from tessdb.error import ReadingKeyError, ReadingTypeError

# ----------------
# Module Constants
# ----------------

INSERT_READING_SQL = '''
    INSERT INTO tess_readings_t (
        date_id,
        time_id,
        tess_id,
        location_id,
        observer_id,
        units_id,
        sequence_number,
        frequency,               
        magnitude,              
        box_temperature,    
        sky_temperature,    
        azimuth,            
        altitude,           
        longitude,          
        latitude,           
        elevation,           
        signal_strength,     
        hash       
    ) VALUES (
        :date_id,
        :time_id,
        :tess_id,
        :location_id,
        :observer_id,
        :units_id,
        :seq,
        :freq1,               
        :mag1,                        
        :box_temperature,    
        :sky_temperature,    
        :az,            
        :alt,           
        :long,          
        :lat,           
        :height,           
        :wdBm,     
        :hash
    )
'''


INSERT_READING4C_SQL = '''
    INSERT INTO tess_readings4c_t (
        date_id,
        time_id,
        tess_id,
        location_id,
        observer_id,
        units_id,
        sequence_number,
        freq1,               
        mag1,              
        freq2,              
        mag2,               
        freq3,              
        mag3,               
        freq4,              
        mag4,               
        box_temperature,    
        sky_temperature,    
        azimuth,            
        altitude,           
        longitude,          
        latitude,           
        elevation,           
        signal_strength,     
        hash       
    ) VALUES (
        :date_id,
        :time_id,
        :tess_id,
        :location_id,
        :observer_id,
        :units_id,
        :seq,
        :freq1,               
        :mag1,              
        :freq2,              
        :mag2,               
        :freq3,              
        :mag3,               
        :freq4,              
        :mag4,               
        :box_temperature,    
        :sky_temperature,    
        :az,            
        :alt,           
        :long,          
        :lat,           
        :height,           
        :wdBm,     
        :hash
    )
'''
# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------


# ============================================================================ #
#                   REAL TIME TESS READNGS (PERIODIC SNAPSHOT FACT TABLE)
# ============================================================================ #

class TESSReadings:

    BUFFER_SIZE = 10
   
    def __init__(self, parent):
        '''Create the SQLite TESS Readings table'''

        self.parent = parent
        self.pool = None
        self.setOptions(auth_filter=True)
        self.resetCounters()
        # Internal buffers to do Block Writes
        self._rows1C = list()
        self._rows4C = list()

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.nreadings = 0
        self.rejNotRegistered = 0
        self.rejNotAuthorised = 0
        self.rejSunrise       = 0
        self.rejDuplicate     = 0
        self.rejOther         = 0


    def getCounters(self):
        '''get stat counters'''
        return [ 
            self.nreadings, 
            self.rejNotRegistered, 
            self.rejNotAuthorised, 
            self.rejSunrise, 
            self.rejDuplicate, 
            self.rejOther
        ]

    # ===============
    # OPERATIONAL API
    # ===============

    def setPool(self, pool):
        self.pool = pool

    @inlineCallbacks
    def update(self, row):
        '''
        Update tess_readings_t with a new row
        Takes care of optional fields
        Returns a Deferred.
        '''
        self._updateCommon(row)
        self._rows1C.append(row)
        if len(self._rows1C) >= self.BUFFER_SIZE:
            yield self.flush(self._rows1C, INSERT_READING_SQL)

    @inlineCallbacks
    def update4C(self, row):
        '''
        Update tess_readings_t with a new row
        Takes care of optional fields
        Returns a Deferred.
        '''
        self._updateCommon(row)
        self._rows4C.append(row)
        if len(self._rows4C) >= self.BUFFER_SIZE:
            yield self.flush(self._rows4C, INSERT_READING4C_SQL)
           
    # ==============
    # Helper methods
    # ==============
 
    @inlineCallbacks
    def _updateCommon(self, row):
        now = row['tstamp'] 
        self.nreadings += 1
        tess = yield self.parent.tess.findPhotometerByName(row)
        log.debug("TESSReadings.update({log_tag}): Found TESS => {tess!s}", tess=tess, log_tag=row['name'])
        if not len(tess):
            log.warn("TESSReadings.update(): No TESS {log_tag} registered ! => {row}", log_tag=row['name'], row=row)
            self.rejNotRegistered += 1
            return None
        tess        = tess[0]  # Keep only the first row of result set
        tess_id     = tess[0]  
        location_id = tess[3]
        authorised  = tess[5] == 1
        observer_id = tess[6]
        # Review authorisation if this filter is enabled
        if self.authFilter and not authorised:
            log.warn("TESSReadings.update({log_tag}): not authorised", log_tag=row['name'])
            self.rejNotAuthorised += 1
            return None
        row['date_id'], row['time_id'] = roundDateTime(now, self.parent.options['secs_resolution'])
        row['tess_id'] = tess_id
        row['location_id'] = location_id
        row['units_id'] = yield self.parent.tess_units.latest(timestamp_source=row['tstamp_src'])
        log.debug("TESSReadings.update({log_tag}): About to write to DB {row!s}", log_tag=row['name'], row=row)

    def setOptions(self, auth_filter):
        '''
        Set filtering Auth
        '''
        self.authFilter = auth_filter


    def database_write(self, rows, sql):
        '''
        Append row in one of the readings table where rows may be 
        - a single row (a dict) or 
        - a sequence of rows (sequence or tuple of dicts)
        Returns a Deferred
        '''
        def _database_write(txn):
            log.debug("{sql} <= {rows}", sql=sql, rows=rows)
            if type(rows) in (list, tuple):
                txn.executemany(sql, rows)
            else:
                txn.execute(sql, rows)
        return self._pool.runInteraction( _database_write)


    @inlineCallbacks
    def flush(self, rows, sql):
        try:
            yield self.database_write(rows)
        except sqlite3.IntegrityError as e:
            log.warn("SQL Integrity error in block write. Looping one by one ...")
            for row in rows:
                try:
                    yield self.database_write(row, sql)
                except sqlite3.IntegrityError as e:
                    log.error("Discarding row by SQL Integrity error: {row}", row=row)
                    self.rejDuplicate += 1
        except Exception as e:
            log.error("TESSReadings.update(): exception {excp!s}. Looping one by one ...", excp=e)
            for row in rows:
                try:
                    yield self.database_write(row, sql)
                except Exception as e:
                    log.error("Discarding row by other SQL error: {row}", row=row)
                    self.rejOther += 1
        rows = list()
