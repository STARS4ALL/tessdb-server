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
from twisted.internet.defer import inlineCallbacks

#--------------
# local imports
# -------------

from   tessdb.error import ReadingKeyError, ReadingTypeError
from   tessdb.sqlite3 import DBase

#-----------------------------------------------
# Auxiliar functions needed to insert locations
# and test updates with daytime filter
# ---------------------------------------------

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

def _assignLocations(transaction, rows):
    '''Assign instrumentto locations'''
    transaction.executemany(
        '''UPDATE tess_t SET location_id = (SELECT location_id FROM location_t WHERE site == :site)
            WHERE tess_t.name == :tess
        ''', rows)


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

# UTC time
TODAY = datetime.datetime(2016, 02, 21, 12, 00, 00)

class FixedInstrumentTestCase(unittest.TestCase):

 
    @inlineCallbacks
    def setUp(self):
        try:
            os.remove('fixed.db')
        except OSError as e:
            pass
        self.db = DBase("fixed.db")
        self.db.tess_readings.setOptions(filter_flag=True, horizon='-0:34')
        yield self.db.schema('foo', '%Y/%m/%d', 2015, 2026, replace=False)
        yield self.insertLocations()
        yield self.registerInstruments()
        yield self.assignLocations()
        
        self.row1 = { 'name': 'TESS-AH',  'seq': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12, }
        self.row2 = { 'name': 'TESS-OAM', 'seq': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12, }

    def tearDown(self):
        self.db.pool.close()

    # --------------
    # Helper methods
    # --------------

    @inlineCallbacks
    def registerInstruments(self):
        tess1 = { 'name': 'TESS-AH',  'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        tess2 = { 'name': 'TESS-OAM', 'mac': '21:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(tess1)
        res = yield self.db.register(tess2)

    @inlineCallbacks
    def insertLocations(self):
        '''
        Insert several locations given by rows dctionary.
        Updates sunrise/sunset accordingly
        '''
        yield self.db.pool.runInteraction( _insertLocations, TEST_LOCATIONS )
        yield self.db.tess_locations.sunrise(batch_perc=100, batch_min_size=1, horizon='-0:34', pause=0, today=TODAY)

    def assignLocations(self):
        assign = [ 
            {'tess': 'TESS-AH',  'site': 'Centro de Recursos Asociativos El Cerro'},
            {'tess': 'TESS-OAM', 'site': 'Observatorio Astronomica de Mallorca'},
        ]
        return self.db.pool.runInteraction( _assignLocations, assign )

    # ----------
    # Test cases
    # ----------

    @inlineCallbacks
    def test_updateAtDaytime(self):
        '''
        Both will be rejected, since the timestamp at both locations 
        is always at day, no matter the day of the year
        '''
        now = datetime.datetime(2016, 02, 21, 13, 00, 00)
        self.row1['tstamp'] = now
        res = yield self.db.update(self.row1)
        self.assertEqual(res, 0x20)
        self.row2['tstamp'] = now
        res = yield self.db.update(self.row2)
        self.assertEqual(res, 0x20)

    @inlineCallbacks
    def test_updateAtNight(self):
        '''
        Both will be accepted, since the timestamp at both locations
        is always at night, no matter the day of the year
        '''
        now = datetime.datetime(2016, 02, 21, 22, 00, 00)
        self.row1['tstamp'] = now
        res = yield self.db.update(self.row1)
        self.assertEqual(res, 0x00)
        self.row2['tstamp'] = now
        res = yield self.db.update(self.row2)
        self.assertEqual(res, 0x00)

    @inlineCallbacks
    def test_updateAtTwilight(self):
        '''
        OAM observatory at night -> acepted
        AH observatory at day -> rejected
        '''
        now = datetime.datetime(2016, 02, 21, 17, 35, 00) 
        self.row1['tstamp'] = now
        res = yield self.db.update(self.row1)
        self.assertEqual(res, 0x20)
        self.row2['tstamp'] = now
        res = yield self.db.update(self.row2)
        self.assertEqual(res, 0x00)



class MobileInstrumentTestCase(unittest.TestCase):

 
    @inlineCallbacks
    def setUp(self):
        try:
            os.remove('mobile.db')
        except OSError as e:
            pass
        self.db = DBase("mobile.db")
        self.db.tess_readings.setOptions(filter_flag=True, horizon='-0:34')
        yield self.db.schema('foo', '%Y/%m/%d', 2015, 2026, replace=False)
        yield self.registerInstruments()

    def tearDown(self):
        self.db.pool.close()

    # --------------
    # Helper methods
    # --------------

    @inlineCallbacks
    def registerInstruments(self):
        tess1 = { 'name': 'TESS-AH',  'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        tess2 = { 'name': 'TESS-OAM', 'mac': '21:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(tess1)
        res = yield self.db.register(tess2)
        self.row1 = { 'name': 'TESS-AH', 'seq': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12, 
            'lat': 40.418561, 'long': -3.551502, 'height': 650.0}
        self.row2 = { 'name': 'TESS-OAM', 'seq': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12, 
            'lat': 39.64269, 'long': 2.950533, 'height': 100.0}

    # ----------
    # Test cases
    # ----------

    @inlineCallbacks
    def test_updateAtDaytime(self):
        '''
        Both will be rejected, since the timestamp at both locations 
        is always at day, no matter the day of the year
        '''
        now = datetime.datetime(2016, 02, 21, 13, 00, 00)
        self.row1['tstamp'] = now
        res = yield self.db.update(self.row1)
        self.assertEqual(res, 0x20)
        self.row2['tstamp'] = now
        res = yield self.db.update(self.row2)
        self.assertEqual(res, 0x20)

    @inlineCallbacks
    def test_updateAtNight(self):
        '''
        Both will be accepted, since the timestamp at both locations
        is always at night, no matter the day of the year
        '''
        now = datetime.datetime(2016, 02, 21, 22, 00, 00)
        self.row1['tstamp'] = now
        res = yield self.db.update(self.row1)
        self.assertEqual(res, 0x00)
        self.row2['tstamp'] = now
        res = yield self.db.update(self.row2)
        self.assertEqual(res, 0x00)

    @inlineCallbacks
    def test_updateAtTwilight(self):
        '''
        OAM observatory at night -> acepted
        AH observatory at day -> rejected
        '''
        now = datetime.datetime(2016, 02, 21, 17, 35, 00) 
        self.row1['tstamp'] = now
        res = yield self.db.update(self.row1)
        self.assertEqual(res, 0x20)
        self.row2['tstamp'] = now
        res = yield self.db.update(self.row2)
        self.assertEqual(res, 0x00)

