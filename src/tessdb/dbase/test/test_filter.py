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
import sys
import datetime
import json

import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.logger import Logger, LogLevel
from twisted.internet.defer import inlineCallbacks

# --------------
# local imports
# -------------

from tessdb.error import ReadingKeyError, ReadingTypeError
from tessdb.dbase.service import DBaseService

# --------------------------------------
# Database Service configuration options
# ---------------------------------------

options = {
    "log_level": "info",
    "register_log_level": "info",
    "type": "sqlite3",
    "connection_string": "tesoro.db",
    "location_filter": True,
    "location_horizon": "-0:34",
    "location_batch_size": 10,
    "location_minimum_batch_size": 1,
    "location_pause": 0,
    "secs_resolution": 5,
}

# -----------------------------------------------
# Auxiliar functions needed to insert locations
# and test updates with daytime filter
# ---------------------------------------------


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


def _assignLocations(transaction, rows):
    """Assign instrumentto locations"""
    transaction.executemany(
        """UPDATE tess_t SET location_id = (SELECT location_id FROM location_t WHERE site == :site)
            WHERE tess_t.name == :tess
        """,
        rows,
    )


TEST_LOCATIONS = [
    {
        "location_id": 0,
        "contact_email": "asociacion@astrohenares.org",
        "site": "Centro de Recursos Asociativos El Cerro",
        "latitude": 40.418561,
        "longitude": -3.55152,
        "elevation": 650,
        "zipcode": "28820",
        "location": "Coslada",
        "province": "Madrid",
        "country": "Spain",
    },
    {
        "location_id": 1,
        "contact_email": "astroam@gmail.com",
        "site": "Observatorio Astronomico de Mallorca",
        "latitude": 39.64269,
        "longitude": 2.950533,
        "elevation": 100,
        "zipcode": "07144",
        "location": "Costitx",
        "province": "Mallorca",
        "country": "Spain",
    },
]

# UTC time
TODAY = ephem.Date(datetime.datetime(2016, 2, 21, 12, 00, 00))


class FixedInstrumentTestCase(unittest.TestCase):
    TEST_INSTRUMENTS = [
        {"name": "TESS-AH", "mac": "12:34:56:78:90:AB", "calib": 10.0},
        {"name": "TESS-OAM", "mac": "21:34:56:78:90:AB", "calib": 10.0},
    ]

    TEST_DEPLOYMENTS1 = [
        {"name": "TESS-AH", "site": "Centro de Recursos Asociativos El Cerro"},
        {"name": "TESS-OAM", "site": "Observatorio Astronomico de Mallorca"},
    ]

    @inlineCallbacks
    def setUp(self):
        try:
            options["connection_string"] = "fixed.db"
            os.remove(options["connection_string"])
            # os.remove('tess_location.json')
            # os.remove('locations.json')
        except OSError as e:
            pass
        with open("locations.json", "w") as f:
            json.dump(TEST_LOCATIONS, f)
        with open("tess_location.json", "w") as f:
            json.dump(self.TEST_DEPLOYMENTS1, f)
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        yield self.registerInstrument()
        yield self.db.reloadService(options)
        self.row1 = {
            "name": "TESS-AH",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "tstamp_src": "Subscriber",
        }
        self.row2 = {
            "name": "TESS-OAM",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "tstamp_src": "Subscriber",
        }

    def tearDown(self):
        self.db.pool.close()

    # --------------
    # Helper methods
    # --------------

    @inlineCallbacks
    def registerInstrument(self):
        for row in self.TEST_INSTRUMENTS:
            yield self.db.register(row)

    # ----------
    # Test cases
    # ----------

    @inlineCallbacks
    def test_updateRejLackSunrise(self):
        """
        Both rejected by lack of sunrise/sunse data in their locations
        """
        now = datetime.datetime(2016, 2, 21, 13, 00, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 2)
        self.assertEqual(self.db.tess_readings.rejSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)

    @inlineCallbacks
    def test_updateAtDaytime(self):
        """
        Both will be rejected, since the timestamp at both locations
        is always at day, no matter the day of the year
        """
        yield self.db.sunrise(today=TODAY)
        now = datetime.datetime(2016, 2, 21, 13, 00, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 2)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)

    @inlineCallbacks
    def test_updateAtNight(self):
        """
        Both will be accepted, since the timestamp at both locations
        is always at night, no matter the day of the year
        """
        yield self.db.sunrise(today=TODAY)
        now = datetime.datetime(2016, 2, 21, 22, 00, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)

    @inlineCallbacks
    def test_updateAtTwilight(self):
        """
        OAM observatory at night -> acepted
        AH observatory at day -> rejected
        """
        yield self.db.sunrise(today=TODAY)
        now = datetime.datetime(2016, 2, 21, 17, 35, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 1)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)


class MobileInstrumentTestCase(unittest.TestCase):
    TEST_INSTRUMENTS = [
        {"name": "TESS-AH", "mac": "12:34:56:78:90:AB", "calib": 10.0},
        {"name": "TESS-OAM", "mac": "21:34:56:78:90:AB", "calib": 10.0},
    ]

    @inlineCallbacks
    def setUp(self):
        try:
            options["connection_string"] = "mobile.db"
            os.remove(options["connection_string"])
        except OSError as e:
            pass
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        yield self.registerInstrument()

        self.row1 = {
            "name": "TESS-AH",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "lat": 40.418561,
            "long": -3.55152,
            "height": 650.0,
            "tstamp_src": "Subscriber",
        }
        self.row2 = {
            "name": "TESS-OAM",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "lat": 39.64269,
            "long": 2.950533,
            "height": 100.0,
            "tstamp_src": "Subscriber",
        }

    def tearDown(self):
        self.db.pool.close()

    # --------------
    # Helper methods
    # --------------

    @inlineCallbacks
    def registerInstrument(self):
        for row in self.TEST_INSTRUMENTS:
            yield self.db.register(row)

    # ----------
    # Test cases
    # ----------

    @inlineCallbacks
    def test_updateAtDaytime(self):
        """
        Both will be rejected, since the timestamp at both locations
        is always at day, no matter the day of the year
        """
        now = datetime.datetime(2016, 2, 21, 13, 00, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 2)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)

    @inlineCallbacks
    def test_updateAtNight(self):
        """
        Both will be accepted, since the timestamp at both locations
        is always at night, no matter the day of the year
        """
        now = datetime.datetime(2016, 2, 21, 22, 00, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)

    @inlineCallbacks
    def test_updateAtTwilight(self):
        """
        OAM observatory at night -> acepted
        AH observatory at day -> rejected
        """
        now = datetime.datetime(2016, 2, 21, 17, 35, 00)
        self.row1["tstamp"] = now
        yield self.db.update(self.row1)
        self.row2["tstamp"] = now
        yield self.db.update(self.row2)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 1)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)
