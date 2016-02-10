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

import datetime
import sqlite3

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue, succeed
from twisted.logger         import Logger

#--------------
# local imports
# -------------
from .utils import Table, TSTAMP_FORMAT, roundDateTime
from ..error import ReadingKeyError, ReadingTypeError
# ----------------
# Module Constants
# ----------------


# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------


# ============================================================================ #
#                   REAL TIME TESS READNGS (PERIODIC SNAPSHOT FACT TABLE)
# ============================================================================ #

class Readings(Table):

   
    def __init__(self, pool, parent):
        '''Create the SQLite TESS Readings table'''
        Table.__init__(self, pool)
        self.parent = parent


    def table(self):
        '''
        Create the SQLite TESS Readings table.
        Returns a Deferred
        '''
        log.info("Creating tess_readings_t Table if not exists")
        return self.pool.runOperation(
            '''
            CREATE TABLE IF NOT EXISTS tess_readings_t
            (
            date_id             INTEGER NOT NULL REFERENCES date_t(date_id), 
            time_id             INTEGER NOT NULL REFERENCES time_t(time_id), 
            tess_id       INTEGER NOT NULL REFERENCES tess_t(tess_id),
            location_id         INTEGER NOT NULL REFERENCES location_t(location_id),
            units_id            INTEGER NOT NULL REFERENCES tess_units_t(units_id),
            sequence_number     INTEGER,
            frequency           REAL,
            magnitude           REAL,
            ambient_temperature REAL,
            sky_temperature     REAL,
            azimuth             REAL,
            altitude            REAL,
            longitude           REAL,
            latitude            REAL,
            height              REAL,
            timestamp           TEXT,
            PRIMARY KEY (date_id, time_id, tess_id)
            );
            '''
        )

    def populate(self, replace):
        return succeed(None)

    # ===============
    # OPERATIONAL API
    # ===============

    @inlineCallbacks
    def update(self, row):
        '''
        Update process
        row is a tuple with the following mandatory keywords:
        - seqno
        - name
        - freq
        - mag
        - tamb
        - tsky
        and the following optional keywords:
        - az
        - alt
        - long
        - lat
        - height
        Returns a Deferred with the following integer resut code as callback value:
        Bit 0 - 1 = new row inserted, 0 = No row inserted
        Bit 6 - 1 = duplicate rows
        Bit 7 - 1 = Other exception
        '''
        ret = 0
        instrument = yield self.parent.instruments.findName(row)
        log.debug("{instrument!s}", instrument=instrument)
        if not len(instrument):
            log.warn("No instrument {0} registered for this reading !".format(row['name']))
            returnValue(ret)
        instrument = instrument[0]  # Keep only the first row
        if not 'tstamp' in row:
            now = datetime.datetime.utcnow()
            row['tstamp'] = now.strftime(TSTAMP_FORMAT)
        else:
            now = row['tstamp']
            row['tstamp'] = row['tstamp'].strftime(TSTAMP_FORMAT)
        row['date_id'], row['time_id'] = roundDateTime(now)
        row['instr_id'] = instrument[0]
        row['loc_id']   = instrument[3]
        row['units_id'] = yield self.parent.units.latest()
        log.debug("{row!s}", row=row)
        n = self.which(row)
        # Get the appropriate decoder function
        myupdater = getattr(self, "update{0}".format(n), None)
        log.debug("found updater for update{0}".format(n))
        try:
            yield myupdater(row)
            ret |= 0x01
        except sqlite3.IntegrityError as e:
            log.error("Instrument id={id} is sending readings too fast", id=instrument[0])
            ret |= 0x40
        except Exception as e:
            log.error("exception {excp!s}", excp=e)
            ret |= 0x80
        returnValue(ret)

    # ==============
    # Helper methods
    # ==============



    def which(self, row):
        '''Find which updateN method must be used'''
        t = 0x00
        incoming  = set(row.keys())
        opt1      = set(['az','alt'])
        opt2      = set(['lat','long','height'])
        if opt1 <= incoming:
            t |= 0x01
        if opt2 <= incoming:
            t |= 0x02
        return t


    def update0(self, row):
        '''
        Insert a new sample into the tabl.Version with no GPS nor Accelerometer
        row is a dictionary with at least the following keys shown in the VALUES clause.
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
                timestamp
            ) VALUES (
                :date_id,
                :time_id,
                :instr_id,
                :loc_id,
                :units_id,
                :seqno,
                :freq,
                :mag,
                :tamb,
                :tsky,
                :tstamp
            )
            ''', row)


    def update1(self, row):
        '''
        Insert a new sample into the table. Version with Accelerometer and no GPS
        row is a dictionary with at least the following keys shown in the VALUES clause.
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
                azimith,
                altitude,
                timestamp
            ) VALUES (
                :date_id,
                :time_id,
                :instr_id,
                :loc_id,
                :units_id,
                :seqno,
                :freq,
                :mag,
                :tamb,
                :tsky,
                :az,
                :alt,
                :tstamp
            )
            ''', row)


    def update2(self, row):
        '''
        Insert a new sample into the table. Version with GPS and no Accelerometer
        row is a dictionary with at least the following keys shown in the VALUES clause.
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
                longitude,
                latitude,
                height,
                timestamp
            ) VALUES (
                :date_id,
                :time_id,
                :instr_id,
                :loc_id,
                :units_id,
                :seqno,
                :freq,
                :mag,
                :tamb,
                :tsky,
                :long,
                :lat,
                :height,
                :tstamp
            )
            ''', row)

    def update3(self, row):
        '''
        Insert a new sample into the table. Version with GPS and Accelerometer
        row is a dictionary with at least the following keys shown in the VALUES clause.
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
                azimith,
                altitude,
                longitude,
                latitude,
                height,
                timestamp
            ) VALUES (
                :date_id,
                :time_id,
                :instr_id,
                :loc_id,
                :units_id,
                :seqno,
                :freq,
                :mag,
                :tamb,
                :tsky,
                :az,
                :alt,
                :long,
                :lat,
                :height,
                :tstamp
            )
            ''', row)
