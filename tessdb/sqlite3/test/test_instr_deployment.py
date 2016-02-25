# ----------------------------------------------------------------------
# Copyright (C) 2015 by Rafael Gonzalez 
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
import sys
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.trial import unittest
from twisted.test  import proto_helpers
from twisted.logger   import Logger, LogLevel
from twisted.internet.defer import inlineCallbacks, returnValue, succeed

#--------------
# local imports
# -------------

import tessdb.sqlite3.tess   # to perform one hack

from   tessdb.error import ReadingKeyError, ReadingTypeError
from   tessdb.sqlite3 import DBase


# Some Sample locations
TEST_LOCATIONS = [
    {
        "location_id"   : 0, 
        "contact_email" : "asociacion@astrohenares.org", 
        "site"          : "Centro de Recursos Asociativos El Cerro", 
        "latitude"      : 40.418561, 
        "longitude"     : -3.551502, 
        "elevation"     : 650, 
        "zipcode"       : '28820', 
        "location"      : "Coslada", 
        "province"      : "Madrid", 
        "country"       : "Spain"
    }, 
    {
        "location_id"   : 1, 
        "contact_email" : "astroam@gmail.com", 
        "site"          : "Observatorio Astronomica de Mallorca", 
        "latitude"      : 39.64269, 
        "longitude"     : 2.950533, 
        "elevation"     : 100, 
        "zipcode"       : '07144', 
        "location"      : "Costitx", 
        "province"      : "Mallorca", 
        "country"       : "Spain"
    }, 
]


TEST_INSTRUMENTS = [
    { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0},
    { 'name': 'test2', 'mac': '12:34:56:78:90:AC', 'calib': 10.0},
]


TEST_DEPLOYMENTS = [
    { 'name': 'test1', 'site': 'Centro de Recursos Asociativos El Cerro'},
    { 'name': 'test2', 'site': 'Observatorio Astronomica de Mallorca'},
]

def _insertLocations(transaction, rows):
    '''Add new locations'''
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


# UTC time
TODAY = datetime.datetime(2016, 02, 21, 12, 00, 00)



class InstrDeployTestCase(unittest.TestCase):

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove('tesoro.db')
        except OSError as e:
            pass
        self.db = DBase("tesoro.db")
        yield self.db.schema('foo', '%Y/%m/%d', 2015, 2026, replace=False)
        yield self.register()
        yield self.locations()

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def locations(self):
        yield self.db.pool.runInteraction( _insertLocations, TEST_LOCATIONS )
        yield self.db.tess_locations.sunrise(batch_perc=100, batch_min_size=1, horizon='-0:34', pause=0, today=TODAY)
       

    @inlineCallbacks
    def register(self):
        for row in TEST_INSTRUMENTS:
            yield self.db.register(row)


    @inlineCallbacks
    def test_assign(self):
        tessdb.sqlite3.tess.DEFAULT_DEPLOYMENT = TEST_DEPLOYMENTS
        yield self.db.tess.populate(replace=True)
        rows = yield self.db.pool.runQuery('SELECT name,location_id FROM tess_t ORDER BY name ASC')
        self.assertEqual( rows[0][0], 'test1')
        self.assertEqual( rows[0][1], 0)
        self.assertEqual( rows[1][0], 'test2')
        self.assertEqual( rows[1][1], 1)
    