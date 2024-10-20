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

# ---------------
# Twisted imports
# ---------------

from twisted.trial import unittest
from twisted.internet.defer import inlineCallbacks

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
    "connection_string": "tesoro.db",
    "location_filter": False,
    "location_horizon": "-0:34",
    "location_batch_size": 10,
    "location_minimum_batch_size": 1,
    "location_pause": 0,
    "secs_resolution": 5,
}


class UpdateUnregisteredTestCase(unittest.TestCase):
    @inlineCallbacks
    def setUp(self):
        try:
            os.remove(options["connection_string"])
        except OSError:
            pass
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def test_updateWithNoInstrument(self):
        """
        Test insert reading with no instrument registered.
        It should not be inserted
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        row = {
            "name": "test1",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "tstamp": now,
            "tstamp_src": "Subscriber",
        }
        yield self.db.update(row)
        self.assertEqual(self.db.tess_readings.nreadings, 1)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 1)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)


class UpdateRegisteredTestCase(unittest.TestCase):
    @inlineCallbacks
    def setUp(self):
        try:
            os.remove(options["connection_string"])
        except OSError:
            pass
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def test_updateWithInstrument(self):
        """
        Test insert a reading with instrument registered.
        It should be inserted
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        row = {
            "name": "test1",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "tstamp": now,
            "tstamp_src": "Subscriber",
        }
        yield self.db.update(row)
        self.assertEqual(self.db.tess_readings.nreadings, 1)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 0)
        self.assertEqual(self.db.tess_readings.rejOther, 0)

    @inlineCallbacks
    def test_updateTooFast(self):
        """
        Test fast inserting two readings with instrument registered.
        The first one should be inserted, the second one not.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        row = {
            "name": "test1",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "tstamp": now,
            "tstamp_src": "Subscriber",
        }
        yield self.db.update(row)
        row = {
            "name": "test1",
            "seq": 1,
            "freq": 1000.01,
            "mag": 12.0,
            "tamb": 0,
            "tsky": -12,
            "tstamp": now,
            "tstamp_src": "Subscriber",
        }
        yield self.db.update(row)
        self.assertEqual(self.db.tess_readings.nreadings, 2)
        self.assertEqual(self.db.tess_readings.rejNotRegistered, 0)
        self.assertEqual(self.db.tess_readings.rejLackSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejSunrise, 0)
        self.assertEqual(self.db.tess_readings.rejDuplicate, 1)
        self.assertEqual(self.db.tess_readings.rejOther, 0)
