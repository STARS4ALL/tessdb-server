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

OPTIONAL_FIELDS = ('az', 'alt', 'long', 'lat', 'height', 'wdBm', 'hash')

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

   
    def __init__(self, parent):
        '''Create the SQLite TESS Readings table'''

        self.parent = parent
        self.pool = None
        self.setOptions(auth_filter=True)
        self.resetCounters()

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
        row = self.to_tess_readings_dict(row)
        now = row['tstamp'] 
        self.nreadings += 1
        ret = 0
        tess = yield self.parent.tess.findPhotometerByName(row)
        log.debug("TESSReadings.update({log_tag}): Found TESS => {tess!s}", tess=tess, log_tag=row['name'])
        if not len(tess):
            log.warn("TESSReadings.update(): No TESS {log_tag} registered !", log_tag=row['name'])
            self.rejNotRegistered += 1
            return None
        tess        = tess[0]  # Keep only the first row of result set
        tess_id     = tess[0]  # fancy aliases for columns
        location_id = tess[3]
        authorised  = tess[5] == 1

        # Review authorisation if this filter is enabled
        if self.authFilter and not authorised:
            log.debug("TESSReadings.update({log_tag}): not authorised", log_tag=row['name'])
            self.rejNotAuthorised += 1
            return None
        row['date_id'], row['time_id'] = roundDateTime(now, self.parent.options['secs_resolution'])
        row['instr_id'] = tess_id
        row['loc_id']   = location_id
        row['units_id'] = yield self.parent.tess_units.latest(timestamp_source=row['tstamp_src'])
        log.debug("TESSReadings.update({log_tag}): About to write to DB {row!s}", log_tag=row['name'], row=row)
        try:
            yield self._update(row)
        except sqlite3.IntegrityError as e:
            # We are experiencing this error lately.
            # With the INSERT OR IGNORE this error could never happen
            # but we keep it like this to trace the number of duplicates
            # Raise the log level so as not to overwhelm the logfile
            log.warn("TESSReadings.update({log_tag}): SQL integrity error for TESS id={id}, new row {row!r}", 
                id=tess_id, log_tag=row['name'], row=row)
            self.rejDuplicate += 1
        except Exception as e:
            log.error("TESSReadings.update({log_tag}): exception {excp!s} for row {row!r}", 
                excp=e, row=row, log_tag=row['name'])
            self.rejOther += 1

    # ==============
    # Helper methods
    # ==============
 
    def to_tess_readings_dict(self, row):
        '''Adapts the dictionary decoded by the MQTT subscriber to the row being written in the database'''
        for key in OPTIONAL_FIELDS:
            row[key] = row.get(key) # create it with None if not already present
        return row

    def setOptions(self, auth_filter):
        '''
        Set filtering Auth
        '''
        self.authFilter     = auth_filter


    def _update(self, row):
        '''
        Insert a new sample into the table.
        '''

        return self.pool.runOperation( 
            '''
            INSERT INTO tess_readings_t (
                date_id,
                time_id,
                tess_id,
                location_id,
                units_id,
                sequence_number,
                frequency,
                magnitude,
                ambient_temperature,
                sky_temperature,
                azimuth,
                altitude,
                longitude,
                latitude,
                height,
                signal_strength,
                hash
            ) VALUES (
                :date_id,
                :time_id,
                :instr_id,
                :loc_id,
                :units_id,
                :seq,
                :freq,
                :mag,
                :tamb,
                :tsky,
                :az,
                :alt,
                :long,
                :lat,
                :height,
                :wdBm,
                :hash
            )
            ''', row)
