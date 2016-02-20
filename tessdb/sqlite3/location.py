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
DEFAULT_LOCATION = [
    {
        "location_id"   : -1, 
        "contact_email" : utils.UNKNOWN, 
        "site"          : utils.UNKNOWN, 
        "longitude"     : utils.UNKNOWN, 
        "latitude"      : utils.UNKNOWN, 
        "elevaion"      : utils.UNKNOWN, 
        "zipcode"       : utils.UNKNOWN, 
        "location"      : utils.UNKNOWN, 
        "province"      : utils.UNKNOWN, 
        "country"       : utils.UNKNOWN
    }, 
]

# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------

def _populateRepl(transaction, rows):
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
            :longitude,
            :latitude,
            :elevation,
            :site,
            :zipcode,
            :location,
            :province,
            :country
        )''', rows)
        
def _populateIgn(transaction, rows):
    '''Dimension initial data loading (ignore flavour)'''
    transaction.executemany(
        '''INSERT OR IGNORE INTO location_t (
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
        log.info("Creating tess_units_t Table if not exists")
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


    def populate(self, replace):
        '''
        Populate the SQLite Location Table
        Returns a Deferred
        '''

        if replace:
            log.info("Replacing Units Table data")
            return self.pool.runInteraction( _populateRepl, self.rows() )
        else:
            log.info("Populating Units Table if empty")
            return self.pool.runInteraction( _populateIgn, self.rows() )


    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject in SQLite API'''
        return fromJSON( os.path.join(self.json_dir, Location.FILE), DEFAULT_LOCATION)


    # ===============
    # OPERATIONAL API
    # ===============

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


    def computeSunrise(self, locations, sun, noon, horizon):
        '''
        Computes sunrise/sunset for a given list of locations.
        Ideally, it needs only to be computed once, after midnight.
        'locations' is a list of tuples (id,longitude,latitude,elevation)
        returned by getLocations() method
        Returns a list of dictionaries ready to be written back to location_t 
        with the following keys:
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
            observer.lon       = math.radians(location[1])
            observer.lat       = math.radians(location[2])
            observer.elevation = location[3]
            row = {}
            row['id']      = location[0]
            row['sunrise'] = str(observer.previous_rising(sun, use_center=True))
            row['sunset']  = str(observer.next_setting(sun, use_center=True))
            rows.append(row)
        return rows


    @inlineCallbacks
    def sunrise(self, batch_perc, batch_min_size, horizon, pause):
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
        sun   = ephem.Sun()
        noon  = ephem.Date(utcnoon())
        while not self.finished:
            locations = yield self.getLocations(index, count)
            if len(locations) :
                rows = yield deferToThread(self.computeSunrise, locations, sun, noon, horizon)
                yield self.updateSunrise(rows)
                log.info("done with index {i}",i=index)
                index += count
                # Pause for some time to smooth I/O & CPU peaks
                yield deferLater(reactor, pause, lambda: None)
            else:
                self.finished = True
        log.info("End sunrise/sunset computation process")
