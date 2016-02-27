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
import math
import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue, succeed
from twisted.logger         import Logger

#--------------
# local imports
# -------------

# -- beware of absolute_import in Python 3 when doing import utils
import utils
from .utils import Table, roundDateTime, isDaytime
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

class TESSReadings(Table):

   
    def __init__(self, pool, parent):
        '''Create the SQLite TESS Readings table'''
        Table.__init__(self, pool)
        self.parent = parent
        self.setOptions(location_filter=True)
        self.resetCounters()

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
            tess_id             INTEGER NOT NULL REFERENCES tess_t(tess_id),
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

    def populate(self, json_dir, replace):
        return succeed(None)

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.nreadings = 0
        self.rejNotRegistered = 0
        self.rejLackSunrise   = 0
        self.rejSunrise       = 0
        self.rejDuplicate     = 0
        self.rejOther         = 0


    def getCounters(self):
        '''get stat counters'''
        return [ 
                self.nreadings, 
                self.rejNotRegistered, 
                self.rejLackSunrise, 
                self.rejSunrise, 
                self.rejDuplicate, 
                self.rejOther
                ]

    # ===============
    # OPERATIONAL API
    # ===============

    @inlineCallbacks
    def update(self, row):
        '''
        Update process
        row is a tuple with the following mandatory keywords:
        - seq
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
        Returns a Deferred.
        '''
        now = row['tstamp'] 
        self.nreadings += 1
        ret = 0
        tess = yield self.parent.tess.findName(row)
        log.debug("{tess!s}", tess=tess)
        if not len(tess):
            log.warn("No tess {0} registered for this reading !".format(row['name']))
            self.rejNotRegistered += 1
            returnValue(None)

        tess = tess[0]  # Keep only the first row
       
        # --------------------------------------------------------------
        # Filter for Daytime if this filter is activated
        # Also filters if lacking enough data.
        # It is very important to assing an instrument a location asap
        # The Unknown location has no sunrise/sunset data
        # --------------------------------------------------------------
        
        if self.locationFilter:
            if  'lat' in row:   # mobile instrument
                self.computeSunrise(row, now)
                if  isDaytime(row['sunrise'], row['sunset'], now):
                    log.debug("reading rejected by being at daytime")
                    self.rejSunrise += 1
                    returnValue(None)
            else:               # fixed instrument assigned to location
                sunrise = yield self.parent.tess_locations.findSunrise(tess[3])
                sunrise = sunrise[0]  # Keep only the first row
                log.debug("Testing sunrise({sunrise!s}) <  now({now!s}) < sunset({sunset!s})", 
                    sunrise=sunrise[0], sunset=sunrise[1], now=now)
                if not sunrise[0]:
                    log.debug("reading rejected by lack of sunrise/sunset data")
                    self.rejLackSunrise += 1
                    returnValue(None)
                if  isDaytime(sunrise[0], sunrise[1], now):
                    log.debug("reading rejected by being at daytime")
                    self.rejSunrise += 1
                    returnValue(None)

        row['date_id'], row['time_id'] = roundDateTime(now)
        row['tstamp']   = now.strftime(utils.TSTAMP_FORMAT)
        row['instr_id'] = tess[0]
        row['loc_id']   = tess[3]
        row['units_id'] = yield self.parent.tess_units.latest()
        log.debug("{row!s}", row=row)
        n = self.which(row)
        # Get the appropriate decoder function
        myupdater = getattr(self, "update{0}".format(n), None)
        try:
            yield myupdater(row)
        except sqlite3.IntegrityError as e:
            log.error("tess id={id} is sending readings too fast", id=tess[0])
            self.rejDuplicate += 1
        except Exception as e:
            log.error("exception {excp!s}", excp=e)
            self.rejOther += 1

    # ==============
    # Helper methods
    # ==============

    def setOptions(self, location_filter=True, location_horizon='-0:34'):
        '''
        Set option for sunrise/sunset filtering
        '''
        self.locationFilter = location_filter
        self.horizon        = location_horizon

    def computeSunrise(self, row, now):
        '''
        Computes sunrise/sunset for a given mobile instrument reading 'row'.
        Leaves the result in the same row of readings, ready to pass the snrise/sunset filter.
        '''
        now = now.replace(hour=12, minute=0, second=0,microsecond=0)
        sun = ephem.Sun(now)
        observer           = ephem.Observer()
        observer.pressure  = 0      # disable refraction calculation
        observer.horizon   = self.horizon
        observer.date      = now
        observer.lon       = math.radians(row['long'])
        observer.lat       = math.radians(row['lat'])
        observer.elevation = row['height']
        row['sunrise']     = observer.previous_rising(sun, use_center=True)
        row['sunset']      = observer.next_setting(sun, use_center=True)
    

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
                :seq,
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
                :seq,
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
                :seq,
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
                :tstamp
            )
            ''', row)
