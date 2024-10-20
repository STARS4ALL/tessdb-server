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

# --------------------
# System wide imports
# -------------------

import os
import datetime
import sqlite3
import json

# ---------------
# Twisted imports
# ---------------

from twisted.trial import unittest
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater

# --------------
# local imports
# -------------

from tessdb.dbase.service import DBaseService

# --------------------------------------
# Database Service configuration options
# ---------------------------------------

options = {
    "log_level": "info",
    "register_log_level": "info",
    "type": "sqlite3",
    "connection_string": "assign.db",
    "location_filter": True,
    "location_horizon": "-0:34",
    "location_batch_size": 10,
    "location_minimum_batch_size": 1,
    "location_pause": 0,
    "secs_resolution": 5,
}

# Some Sample locations
TEST_LOCATIONS = [
    {
        "location_id": 0,
        "contact_email": "asociacion@astrohenares.org",
        "site": "Centro de Recursos Asociativos El Cerro",
        "latitude": 40.418561,
        "longitude": -3.551502,
        "elevation": 650,
        "zipcode": "28820",
        "location": "Coslada",
        "province": "Madrid",
        "country": "Spain",
    },
    {
        "location_id": 1,
        "contact_email": "astroam@gmail.com",
        "site": "Observatorio Astronomica de Mallorca",
        "latitude": 39.64269,
        "longitude": 2.950533,
        "elevation": 100,
        "zipcode": "07144",
        "location": "Costitx",
        "province": "Mallorca",
        "country": "Spain",
    },
]


def _insertLocations(transaction, rows):
    """Add new locations"""
    transaction.executemany(
        """INSERT OR REPLACE INTO location_t (
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
        )""",
        rows,
    )


# UTC time
TODAY = datetime.datetime(2016, 2, 21, 12, 00, 00)


class InstrDeployTestCase1(unittest.TestCase):
    TEST_INSTRUMENTS = [
        {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0},
        {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 10.0},
        {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 15.0},
        {"name": "test3", "mac": "12:34:56:78:90:AD", "calib": 10.0},
        {"name": "test3", "mac": "12:34:56:78:90:AD", "calib": 17.0},
        {"name": "test4", "mac": "12:34:56:78:90:AE", "calib": 10.0},
    ]

    TEST_DEPLOYMENTS1 = [
        {"name": "test1", "site": "Centro de Recursos Asociativos El Cerro"},
        {"name": "test2", "site": "Observatorio Astronomica de Mallorca"},
    ]

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove(options["connection_string"])
            os.remove("tess_location.json")
            os.remove("locations.json")
        except OSError:
            pass
        with open("locations.json", "w") as f:
            json.dump(TEST_LOCATIONS, f)
        with open("tess_location.json", "w") as f:
            json.dump(self.TEST_DEPLOYMENTS1, f)
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        yield self.registerInstrument()

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def registerInstrument(self):
        for row in self.TEST_INSTRUMENTS:
            yield deferLater(reactor, 0, lambda: None)
            yield self.db.register(row)

    @inlineCallbacks
    def test_assign_ok(self):
        yield self.db.reloadService(options)
        rows = yield self.db.pool.runQuery(
            "SELECT name,location_id,tess_id FROM tess_t ORDER BY tess_id ASC"
        )
        self.assertEqual(rows[0][0], "test1")
        self.assertEqual(rows[0][2], 1)
        self.assertEqual(rows[0][1], 0)

        self.assertEqual(rows[1][0], "test2")
        self.assertEqual(rows[1][2], 2)
        self.assertEqual(rows[1][1], 1)

        self.assertEqual(rows[2][0], "test2")
        self.assertEqual(rows[2][2], 3)
        self.assertEqual(rows[2][1], 1)

        self.assertEqual(rows[3][0], "test3")
        self.assertEqual(rows[3][2], 4)
        self.assertEqual(rows[3][1], -1)

        self.assertEqual(rows[4][0], "test3")
        self.assertEqual(rows[4][2], 5)
        self.assertEqual(rows[4][1], -1)

        self.assertEqual(rows[5][0], "test4")
        self.assertEqual(rows[5][2], 6)
        self.assertEqual(rows[5][1], -1)


class InstrDeployTestCase2(unittest.TestCase):
    TEST_INSTRUMENTS = [
        {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0},
        {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 10.0},
        {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 15.0},
        {"name": "test3", "mac": "12:34:56:78:90:AD", "calib": 10.0},
        {"name": "test3", "mac": "12:34:56:78:90:AD", "calib": 17.0},
        {"name": "test4", "mac": "12:34:56:78:90:AE", "calib": 10.0},
    ]

    TEST_DEPLOYMENTS2 = [
        {"name": "test1", "site": "Centro Equivocado"},
        {"name": "test2", "site": "Observatorio Astronomica de Mallorca"},
    ]

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove(options["connection_string"])
            os.remove("tess_location.json")
            os.remove("locations.json")
        except OSError:
            pass
        with open("locations.json", "w") as f:
            json.dump(TEST_LOCATIONS, f)
        with open("tess_location.json", "w") as f:
            json.dump(self.TEST_DEPLOYMENTS2, f)
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        yield self.registerInstrument()

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def registerInstrument(self):
        for row in self.TEST_INSTRUMENTS:
            yield deferLater(reactor, 0, lambda: None)
            yield self.db.register(row)

    def test_assign_wrong_loc(self):
        d = self.db.reloadService(options)
        return self.assertFailure(d, sqlite3.IntegrityError)


class InstrDeployTestCase3(unittest.TestCase):
    TEST_INSTRUMENTS = [
        {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0},
        {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 10.0},
        {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 15.0},
        {"name": "test3", "mac": "12:34:56:78:90:AD", "calib": 10.0},
        {"name": "test3", "mac": "12:34:56:78:90:AD", "calib": 17.0},
        {"name": "test4", "mac": "12:34:56:78:90:AE", "calib": 10.0},
    ]

    TEST_DEPLOYMENTS1 = [
        {"name": "test1", "site": "Centro de Recursos Asociativos El Cerro"},
        {"name": "test2", "site": "Observatorio Astronomica de Mallorca"},
    ]

    TEST_DEPLOYMENTS3 = [
        {"name": "wrong-tess1", "site": "Centro de Recursos Asociativos El Cerro"},
        {"name": "wrong-tess2", "site": "Observatorio Astronomico de Mallorca"},
    ]

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove(options["connection_string"])
        except OSError:
            pass
        with open("locations.json", "w") as f:
            json.dump(TEST_LOCATIONS, f)
        with open("tess_location.json", "w") as f:
            json.dump(self.TEST_DEPLOYMENTS1, f)
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        yield self.registerInstrument()
        yield self.db.reloadService(options)

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def registerInstrument(self):
        for row in self.TEST_INSTRUMENTS:
            yield deferLater(reactor, 0, lambda: None)
            yield self.db.register(row)

    @inlineCallbacks
    def test_assign_wrong_instr(self):
        with open("tess_location.json", "w") as f:
            json.dump(self.TEST_DEPLOYMENTS3, f)
        _ = self.db.reloadService(options)
        rows = yield self.db.pool.runQuery(
            "SELECT name,location_id,tess_id FROM tess_t ORDER BY tess_id ASC"
        )
        self.assertEqual(rows[0][0], "test1")
        self.assertEqual(rows[0][2], 1)
        self.assertEqual(rows[0][1], 0)

        self.assertEqual(rows[1][0], "test2")
        self.assertEqual(rows[1][2], 2)
        self.assertEqual(rows[1][1], 1)

        self.assertEqual(rows[2][0], "test2")
        self.assertEqual(rows[2][2], 3)
        self.assertEqual(rows[2][1], 1)
