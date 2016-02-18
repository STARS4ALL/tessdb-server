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
from ephem import cities

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger         import Logger

#--------------
# local imports
# -------------

# -- beware of absolute_import in Python 3 when doing import utils
import utils
from .utils import Table, fromJSON

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
            location_id             INTEGER PRIMARY KEY,
            contact_email           TEXT,
            site                    TEXT,
            longitude               REAL,
            latitude                REAL,
            elevation               REAL,
            zipcode                 TEXT,
            location                TEXT,
            province                TEXT,
            country                 TEXT
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


