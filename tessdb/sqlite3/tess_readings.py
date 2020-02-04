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

from tessdb.logger import setLogLevel

from tessdb.sqlite3.utils import Table, roundDateTime, isDaytime
from tessdb.error import ReadingKeyError, ReadingTypeError

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

   
    def __init__(self, connection, parent):
        '''Create the SQLite TESS Readings table'''

        Table.__init__(self, connection)
        self.parent = parent
        self.setOptions(auth_filter=True, location_filter=True)
        self.resetCounters()


    def table(self):
        '''
        Create the SQLite TESS Readings table.
        '''
        log.info("Creating tess_readings_t Table if not exists")
        self.connection.execute(
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
            signal_strength     INTEGER,
            PRIMARY KEY (date_id, time_id, tess_id)
            );
            '''
        )
        self.connection.commit()

    def populate(self, json_dir):
        return

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
        tess = yield self.parent.tess.findPhotometerByName(row)
        log.debug("TESSReadings.update({log_tag}): Found TESS => {tess!s}", tess=tess, log_tag=row['name'])
        if not len(tess):
            log.warn("TESSReadings.update(): No TESS {log_tag} registered !", log_tag=row['name'])
            self.rejNotRegistered += 1
            returnValue(None)

        tess        = tess[0]  # Keep only the first row of result set
        tess_id     = tess[0]  # fancy aliases for columns
        location_id = tess[3]
        authorised  = tess[5] == 1

        # Review authorisation if this filtering is enabled
        if self.authFilter and not authorised:
            log.debug("TESSReadings.update({log_tag}): not authorised", log_tag=row['name'])
            self.rejNotAuthorised += 1
            returnValue(None)

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
                    log.debug("TESSReadings.update({log_tag}): reading rejected at daytime", log_tag=row['name'])
                    self.rejSunrise += 1
                    returnValue(None)
            else:               # fixed instrument assigned to location
                riseset = yield self.parent.tess_locations.findSunrise(location_id)
                riseset = riseset[0]  # Keep only the first row
                sunrise = riseset[0]
                sunset  = riseset[1]
                log.debug("TESSReadings.update({log_tag}): testing sunrise({sunrise!s}) <  now({now!s}) < sunset({sunset!s})", 
                    log_tag=row['name'], sunrise=sunrise, sunset=sunset, now=now)
                if not sunrise:
                    log.debug("TESSReadings.update({log_tag}): reading accepted even if no sunrise/sunset data", 
                        log_tag=row['name'])
                elif isDaytime(sunrise, sunset, now):
                    log.debug("TESSReadings.update({log_tag}): reading rejected at daytime", log_tag=row['name'])
                    self.rejSunrise += 1
                    returnValue(None)

        row['date_id'], row['time_id'] = roundDateTime(now, self.parent.time.secs_resol)
        row['instr_id'] = tess_id
        row['loc_id']   = location_id
        row['units_id'] = yield self.parent.tess_units.latest(timestamp_source=row['tstamp_src'])
        log.debug("TESSReadings.update({log_tag}): About to write to DB {row!s}", log_tag=row['name'], row=row)
        n = self.which(row)
        # Get the appropriate decoder function
        myupdater = getattr(self, "update{0}".format(n), None)
        try:
            yield myupdater(row)
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

    def setOptions(self, auth_filter, location_filter, location_horizon='-0:34'):
        '''
        Set filtering. Auth and sunrise/sunset
        '''
        self.authFilter     = auth_filter
        self.locationFilter = location_filter
        self.horizon        = location_horizon

    def computeSunrise(self, row, now):
        '''
        Computes sunrise/sunset for a given mobile instrument reading 'row'.
        Leaves the result in the same row of readings, ready to pass the snrise/sunset filter.
        '''
        utcnoon = ephem.Date(now.replace(hour=12, minute=0, second=0,microsecond=0))
        midnight = ephem.Date(utcnoon - 12 * ephem.hour)
        sun = ephem.Sun(utcnoon)
        observer           = ephem.Observer()
        observer.pressure  = 0      # disable refraction calculation
        observer.horizon   = self.horizon
        observer.date      = utcnoon
        observer.lon       = math.radians(row['long'])
        observer.lat       = math.radians(row['lat'])
        observer.elevation = row['height']
        # In locations near Grenwich: (prev) sunrise < (next) sunset
        # In location far away from Greenwich: (prev) sunset < (next) sunrise
        prev_sunrise = observer.previous_rising(sun, use_center=True)
        next_sunset  = observer.next_setting(sun, use_center=True)
        prev_sunset  = observer.previous_setting(sun, use_center=True)
        next_sunrise = observer.next_rising(sun, use_center=True)
        if prev_sunrise < midnight: # Far West from Greenwich
            sunrise = str(next_sunrise)
            sunset  = str(prev_sunset)
        else:                       # Our normal case in Spain
            sunrise = str(prev_sunrise)
            sunset  = str(next_sunset)
        row['sunrise']     = sunrise
        row['sunset']      = sunset
    

    def which(self, row):
        '''Find which updateN method must be used'''
        t = 0x00
        incoming  = set(row.keys())
        opt1      = set(['az','alt'])
        opt2      = set(['lat','long','height'])
        opt3      = set(['wdBm']) 
        if opt1 <= incoming:
            t |= 0x01
        if opt2 <= incoming:
            t |= 0x02
        if opt3 <= incoming:
            t |= 0x04
        return t

    def update0(self, row):
        '''
        Insert a new sample into the table. Version with:
        - no GPS nor Accelerometer
        - no Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                sky_temperature
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
                :tsky
            )
            ''', row)


    def update1(self, row):
        '''
        Insert a new sample into the table. 
        Version with:
        - Accelerometer and no GPS
        - no Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                altitude
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
                :alt
            )
            ''', row)


    def update6(self, row):
        '''
        Insert a new sample into the table. Version with:
        - GPS and no Accelerometer
        - no Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                height
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
                :height
            )
            ''', row)

    def update3(self, row):
        '''
        Insert a new sample into the table. Version with:
        - GPS and Accelerometer
        - no Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                height
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
                :height
            )
            ''', row)


    def update4(self, row):
        '''
        Insert a new sample into the table. Version with:
        - no GPS nor Accelerometer
        - Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                signal_strength
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
                :wdBm
            )
            ''', row)


    def update5(self, row):
        '''
        Insert a new sample into the table. 
        Version with:
        - Accelerometer and no GPS
        - Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                signal_strength
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
                :wdBm
            )
            ''', row)


    def update6(self, row):
        '''
        Insert a new sample into the table. Version with:
        - GPS and no Accelerometer
        - Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                signal_strength
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
                :wdBm
            )
            ''', row)

    def update7(self, row):
        '''
        Insert a new sample into the table. Version with:
        - GPS and Accelerometer
        - Received Signal Strength
        'row' is a dictionary with at least the following keys shown in the VALUES clause.
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
                signal_strength
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
                :wdBm
            )
            ''', row)
