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
import math
import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.internet         import reactor, defer
from twisted.internet.defer   import inlineCallbacks, returnValue
from twisted.logger           import Logger
from twisted.internet.threads import deferToThread
from twisted.internet.task    import deferLater

#--------------
# local imports
# -------------

from   tessdb.sqlite3.utils import Table, fromJSON, utcnoon, UNKNOWN, NEVER_UP, ALWAYS_UP

# ----------------
# Module Constants
# ----------------

OUT_OF_SERVICE = 'Out of Service'

# default locations if no JSON file is found 
# Longitude/latitude are used in tessdb for sunrise/sunset calculation
DEFAULT_LOCATION = {
    "location_id"   : -1, 
    "contact_name"  : UNKNOWN,
    "contact_email" : UNKNOWN,
    "organization"  : UNKNOWN,
    "site"          : UNKNOWN, 
    "longitude"     : UNKNOWN, 
    "latitude"      : UNKNOWN, 
    "elevation"     : UNKNOWN, 
    "zipcode"       : UNKNOWN, 
    "location"      : UNKNOWN, 
    "province"      : UNKNOWN, 
    "country"       : UNKNOWN
} 

OUT_OF_SERVICE_LOCATION = {
    "location_id"   : -2, 
    "contact_name"  : UNKNOWN, 
    "contact_email" : UNKNOWN, 
    "organization"  : UNKNOWN,
    "site"          : OUT_OF_SERVICE, 
    "longitude"     : UNKNOWN, 
    "latitude"      : UNKNOWN, 
    "elevation"     : UNKNOWN, 
    "zipcode"       : UNKNOWN, 
    "location"      : UNKNOWN, 
    "province"      : UNKNOWN, 
    "country"       : UNKNOWN
} 

# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------


def _updateSunrise(transaction, rows):
    '''Update sunrise/sunset in given rows'''
    transaction.executemany(
        '''
        UPDATE location_t SET sunrise = :sunrise, sunset = :sunset
        WHERE location_id == :id
        ''', rows)
       
# ============================================================================ #
#                               LOCATION TABLE (DIMENSION)
# ============================================================================ #

# This table does not represent the exact instrument location 
# but the general area where is deployed.

class Location(Table):

    FILE = 'locations.json'

    def __init__(self, connection):
        '''Create and populate the SQLite Location Table'''
        Table.__init__(self, connection)
        self._cache = dict()

    # ==========
    # SCHEMA API
    # ==========

    def table(self):
        '''
        Create the SQLite Location table
        Returns a Deferred
        '''
        log.info("Creating location_t Table if not exists")
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS location_t
            (
            location_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_email           TEXT,
            site                    TEXT,
            longitude               REAL,
            latitude                REAL,
            elevation               REAL,
            zipcode                 TEXT,
            location                TEXT,
            province                TEXT,
            country                 TEXT,
            sunrise                 TEXT,
            sunset                  TEXT,
            contact_name            TEXT,
            timezone                TEXT DEFAULT 'Etc/UTC',
            organization            TEXT
            );
            '''
        )
        self.connection.commit()


    def populate(self, json_dir):
        '''
        Populate the SQLite Location Table
        '''
        read_rows = self.rows(json_dir)
        log.info("Populating/Replacing Units Table data")
        self.connection.executemany( 
            '''INSERT OR REPLACE INTO location_t (
            location_id,
            contact_name,
            contact_email,
            organization,
            site,
            longitude,
            latitude,
            elevation,
            zipcode,
            location,
            province,
            country
        ) VALUES (
            :location_id,
            :contact_name,
            :contact_email,
            :organization,
            :site,
            :longitude,
            :latitude,
            :elevation,
            :zipcode,
            :location,
            :province,
            :country
        )''', read_rows)
        self.connection.commit()
      


    # --------------
    # Helper methods
    # --------------


    def rows(self, json_dir):
        '''Generate a list of rows to inject in SQLite API'''
        read_rows = fromJSON(os.path.join(json_dir, Location.FILE), [DEFAULT_LOCATION])
        read_rows.append(DEFAULT_LOCATION)
        read_rows.append(OUT_OF_SERVICE_LOCATION)
        return (read_rows)

    def invalidCache(self):
        '''Invalid sunrise/sunset cache'''
        log.info("location_t sunset cache invalidated with size = {size}", size=len(self._cache))
        self._cache = dict()

    def updateCache(self, resultset, loc_id):
        '''Update sunrise/asunset cache if found'''
        if(len(resultset)):
            self._cache[loc_id] = resultset
        return resultset


    # ===============
    # OPERATIONAL API
    # ===============

    def findSunrise(self, ident):
        '''
        Find location given by 'ident'
        Returns a Deferred.
        '''
        if ident in self._cache.keys():
            return defer.succeed(self._cache.get(ident))

        param = {'id': ident }
        d = self.pool.runQuery(
            '''
            SELECT sunrise, sunset 
            FROM location_t 
            WHERE location_id == :id
            ''', param)
        d.addCallback(self.updateCache, ident)
        return d

    def getLocations(self, index, count):
        '''
        Get 'count' locations starting from 'index'
        This query is optimized for SQLite.
        Returns a Deferred.
        '''
        param = {'id': index, 'count': count }
        return self.pool.runQuery(
            '''
            SELECT location_id, longitude, latitude, elevation, site 
            FROM location_t 
            WHERE location_id >= :id
            ORDER BY location_id
            LIMIT :count 
            ''', param)

    def updateSunrise(self, rows):
        '''
        Update sunrise/sunset in given rows.
        Rows is a dictionary with at least the following keys:
        - 'id'
        - 'sunrise'
        - 'sunset'
        Returns a Deferred.
        '''
        return self.pool.runInteraction( _updateSunrise, rows )


    def validPosition(self, location):
        '''
        Test for valid longitude,latitude elevation in result set.

        location[1] - longitude
        location[2] - latitude
        location[3] - elevation
        '''
        return location[1] and location[1] != UNKNOWN and  location[2] and location[2] != UNKNOWN and location[3] and location[3] != UNKNOWN
    

    def computeSunrise(self, locations, sun, noon, horizon):
        '''
        Computes sunrise/sunset for a given list of locations.
        Ideally, it needs only to be computed once, after midnight.
        'locations' is a list of tuples (id,longitude,latitude,elevation)
        returned by getLocations() method
        Returns a list of dictionaries ready to be written back to location_t 
        table with the following keys:
        - id
        - 'sunrise'
        - 'sunset'
        '''
        observer = ephem.Observer()
        observer.pressure  = 0      # disable refraction calculation
        observer.horizon   = horizon
        observer.date      = noon
        midnight = ephem.Date(utcnoon() - 12 * ephem.hour)
        rows = []
        for location in locations:
            if self.validPosition(location):
                observer.lon       = math.radians(location[1])
                observer.lat       = math.radians(location[2])
                observer.elevation = location[3]
                site               = location[4]
                # In locations near Grenwich: (prev) sunrise < (next) sunset
                # In location far away from Greenwich: (prev) sunset < (next) sunrise
                # Circumpolar sites may raise exceptions
                try:
                    prev_sunrise = observer.previous_rising(sun, use_center=True)
                    next_sunset  = observer.next_setting(sun, use_center=True)
                    prev_sunset  = observer.previous_setting(sun, use_center=True)
                    next_sunrise = observer.next_rising(sun, use_center=True)
                except ephem.NeverUpError as e:
                    sunrise = NEVER_UP
                    sunset  = NEVER_UP
                except ephem.AlwaysUpError as e:
                    sunrise = ALWAYS_UP
                    sunset  = ALWAYS_UP
                else:
                    if prev_sunrise < midnight: # Far West from Greenwich
                        log.debug("{site}: Chose Far West from Greenwich", site=site)
                        sunrise = str(next_sunrise)
                        sunset  = str(prev_sunset)
                    else:                       # Our normal case in Spain
                        log.debug("{site}: Chose our normal case in Spain", site=site)
                        sunrise = str(prev_sunrise)
                        sunset  = str(next_sunset)
                finally:
                    rows.append ({ 
                        'id'     : location[0], 
                        'sunrise': sunrise,
                        'sunset' : sunset,
                        'site'   : site
                    })
        return rows


    @inlineCallbacks
    def sunrise(self, batch_perc=0, batch_min_size=1, horizon='-0:34', pause=0, today=utcnoon()):
        '''
        This is the long running process that iterates all locations in the table
        computing their sunrise/sunset and storing them back to the database.
        It may take a while so it is divided in batches to smooth CPU and I/O peaks
        '''
       
        log.info("Begin sunrise/sunset computation process for {today!s}", today=today)
        self.finished = False
        nlocations = yield self.pool.runQuery('SELECT count(*) FROM location_t WHERE location_id >= 0')
        index = 0
        count = int( batch_perc * 0.01 * nlocations[0][0] )
        count = max(count,  batch_min_size)
        today = ephem.Date(today)
        sun   = ephem.Sun(today)
        while not self.finished:
            locations = yield self.getLocations(index, count)
            if len(locations) :
                rows = yield deferToThread(self.computeSunrise, locations, sun, today, horizon)
                log.debug("sunrise/sunset: rows {rows!s}", rows=rows)
                yield self.updateSunrise(rows)
                log.debug("sunrise/sunset: done with index {i}",i=index)
                index += count
                # Pause for some time to smooth I/O & CPU peaks
                yield deferLater(reactor, pause, lambda: None)
            else:
                self.finished = True
        log.info("End sunrise/sunset computation process")
