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

# ---------------
# Twisted imports
# ---------------

from twisted.internet         import reactor, defer
from twisted.internet.defer   import inlineCallbacks
from twisted.logger           import Logger


#--------------
# local imports
# -------------

from   tessdb.sqlite3.utils import Table, UNKNOWN

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
            contact_name            TEXT,
            timezone                TEXT DEFAULT 'Etc/UTC',
            organization            TEXT
            );
            '''
        )
        self.connection.commit()


    def populate(self):
        '''
        Populate the SQLite Location Table
        '''
        read_rows = self.rows()
        log.info("Populating/Replacing Units Table with default data")
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


    def rows(self):
        '''Generate a list of rows to inject in SQLite API'''
        read_rows = []
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
  
