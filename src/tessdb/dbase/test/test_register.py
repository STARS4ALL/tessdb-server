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


class RegistryNominalTestCase(unittest.TestCase):
    @inlineCallbacks
    def setUp(self):
        try:
            os.remove(options["connection_string"])
        except OSError:
            pass
        self.db = DBaseService(parent=None, options=options)
        yield self.db.schema()
        self.db.tess.resetCounters()

    def tearDown(self):
        self.db.pool.close()

    @inlineCallbacks
    def test_registerOneInstrument(self):
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 1)
        self.assertEqual(self.db.tess.nCreation, 1)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 0)
        self.assertEqual(self.db.tess.rejUpdDupName, 0)
        self.assertEqual(self.db.tess.nUpdCalibChange, 0)

    @inlineCallbacks
    def test_registerSameInstrTwice(self):
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 2)
        self.assertEqual(self.db.tess.nCreation, 1)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 0)
        self.assertEqual(self.db.tess.rejUpdDupName, 0)
        self.assertEqual(self.db.tess.nUpdCalibChange, 0)

    @inlineCallbacks
    def test_changeNameOnly(self):
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test2", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 2)
        self.assertEqual(self.db.tess.nCreation, 1)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 1)
        self.assertEqual(self.db.tess.rejUpdDupName, 0)
        self.assertEqual(self.db.tess.nUpdCalibChange, 0)

    @inlineCallbacks
    def test_changeConstantOnly(self):
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 17.0}
        yield self.db.register(row)
        # self.assertEqual(res, 0x01 | 0x04)
        self.assertEqual(self.db.tess.nregister, 2)
        self.assertEqual(self.db.tess.nCreation, 1)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 0)
        self.assertEqual(self.db.tess.rejUpdDupName, 0)
        self.assertEqual(self.db.tess.nUpdCalibChange, 1)

    @inlineCallbacks
    def test_changeNameAndConstant(self):
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test2", "mac": "12:34:56:78:90:AB", "calib": 17.0}
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 2)
        self.assertEqual(self.db.tess.nCreation, 1)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 1)
        self.assertEqual(self.db.tess.rejUpdDupName, 0)
        self.assertEqual(self.db.tess.nUpdCalibChange, 1)

    @inlineCallbacks
    def test_failChangeName(self):
        """
        Fail to change the second instrument name to the first's one
        """
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test1", "mac": "12:34:56:78:90:AC", "calib": 10.0}
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 3)
        self.assertEqual(self.db.tess.nCreation, 2)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 0)
        self.assertEqual(self.db.tess.rejUpdDupName, 1)
        self.assertEqual(self.db.tess.nUpdCalibChange, 0)

    @inlineCallbacks
    def test_failRegisterNew(self):
        """
        Fail to register a second instrument with different MAC but same name
        """
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test1", "mac": "12:34:56:78:90:AC", "calib": 10.0}
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 2)
        self.assertEqual(self.db.tess.nCreation, 1)
        self.assertEqual(self.db.tess.rejCreaDupName, 1)
        self.assertEqual(self.db.tess.nUpdNameChange, 0)
        self.assertEqual(self.db.tess.rejUpdDupName, 0)
        self.assertEqual(self.db.tess.nUpdCalibChange, 0)

    @inlineCallbacks
    def test_failChangeNameConstantOk(self):
        """
        Fail to change the second instrument name to the first's one
        but changes constant ok.
        """
        row = {"name": "test1", "mac": "12:34:56:78:90:AB", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test2", "mac": "12:34:56:78:90:AC", "calib": 10.0}
        yield self.db.register(row)
        row = {"name": "test1", "mac": "12:34:56:78:90:AC", "calib": 17.0}
        yield self.db.register(row)
        self.assertEqual(self.db.tess.nregister, 3)
        self.assertEqual(self.db.tess.nCreation, 2)
        self.assertEqual(self.db.tess.rejCreaDupName, 0)
        self.assertEqual(self.db.tess.nUpdNameChange, 0)
        self.assertEqual(self.db.tess.rejUpdDupName, 1)
        self.assertEqual(self.db.tess.nUpdCalibChange, 1)
