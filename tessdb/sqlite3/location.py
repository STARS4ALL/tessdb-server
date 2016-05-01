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
import math
import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger         import Logger
from twisted.internet.threads import deferToThread
from twisted.internet.task import deferLater

#--------------
# local imports
# -------------

# -- beware of absolute_import in Python 3 when doing import utils
import utils
from .utils import Table, fromJSON, utcnoon

# ----------------
# Module Constants
# ----------------

# default location if no JSON file is found 
# Longitude/latitude are used in tessdb for sunrise/sunset calculation
DEFAULT_LOCATION = {
    "location_id"   : -1, 
    "contact_email" : utils.UNKNOWN, 
    "site"          : utils.UNKNOWN, 
    "longitude"     : utils.UNKNOWN, 
    "latitude"      : utils.UNKNOWN, 
    "elevation"     : utils.UNKNOWN, 
    "zipcode"       : utils.UNKNOWN, 
    "location"      : utils.UNKNOWN, 
    "province"      : utils.UNKNOWN, 
    "country"       : utils.UNKNOWN
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
        '''INSERT OR REPLACE INTO location_t (
            location_id,
            contact_email,
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
            :contact_email,
            :site,
            :longitude,
            :latitude,
            :elevation,
            :zipcode,
            :location,
            :province,
            :country
        )''', rows)
        

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

    def __init__(self, pool):
        '''Create and populate the SQLite Location Table'''
        Table.__init__(self, pool)

    # ==========
    # SCHEMA API
    # ==========

    def table(self):
        '''
        Create the SQLite Location table
        Returns a Deferred
        '''
        log.info("Creating location_t Table if not exists")
        return self.pool.runOperation(
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
            sunset                  TEXT
            );
            '''
        )


    @inlineCallbacks
    def populate(self, json_dir):
        '''
        Populate the SQLite Location Table
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
        read_rows = yield deferToThread(fromJSON, os.path.join(json_dir, Location.FILE), [DEFAULT_LOCATION])
        read_rows.append(DEFAULT_LOCATION)
        returnValue(read_rows)

    # ===============
    # OPERATIONAL API
    # ===============

    def findSunrise(self, ident):
        '''
        Find location given by 'ident'
        Returns a Deferred.
        '''
        param = {'id': ident }
        return self.pool.runQuery(
            '''
            SELECT sunrise, sunset 
            FROM location_t 
            WHERE location_id == :id
            ''', param)

    def getLocations(self, index, count):
        '''
        Get 'count' locations starting from 'index'
        This query is optimized for SQLite.
        Returns a Deferred.
        '''
        param = {'id': index, 'count': count }
        return self.pool.runQuery(
            '''
            SELECT location_id, longitude, latitude, elevation 
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
        '''
        return location[1] and location[1] != utils.UNKNOWN and  location[2] and location[2] != utils.UNKNOWN and location[3] and location[2] != utils.UNKNOWN
    

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
        rows = []
        for location in locations:
            if self.validPosition(location):
                observer.lon       = math.radians(location[1])
                observer.lat       = math.radians(location[2])
                observer.elevation = location[3]
                rows.append ({ 
                    'id'     : location[0], 
                    'sunrise': str(observer.previous_rising(sun, use_center=True)),
                    'sunset' : str(observer.next_setting(sun, use_center=True))
                })
        return rows


    @inlineCallbacks
    def sunrise(self, batch_perc=0, batch_min_size=1, horizon='-0:34', pause=0, today=utcnoon()):
        '''
        This is the long running process that iterates all locations in the table
        computing their sunrise/sunset and storing them back to the database.
        It may take a while so it is divided in batches to smooth CPU and I/O peaks
        '''
       
        log.info("Begin sunrise/sunset computation process")
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
