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


class RegistryNominalTestCase(unittest.TestCase):

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove('tesoro.db')
        except OSError as e:
            pass
        self.db = DBase("tesoro.db")
        yield self.db.schema('foo', '%Y/%m/%d', 2015, 2026, True, '-0:34', replace=False)

    def tearDown(self):
        self.db.pool.close()
    
    @inlineCallbacks
    def test_register1(self):
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)

    @inlineCallbacks
    def test_register2(self):
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        res = yield self.db.register(row)
        self.assertEqual(res, 0x01)

    @inlineCallbacks
    def test_changeNameOnly(self):
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test2', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x01 | 0x02)
    
    @inlineCallbacks
    def test_changeConstantOnly(self):
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 18.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x01 | 0x04)
    
    @inlineCallbacks
    def test_changeNameAndConstant(self):
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test2', 'mac': '12:34:56:78:90:AB', 'calib': 18.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x01 | 0x02 | 0x04)

    @inlineCallbacks
    def test_failChangeName(self):
        '''
        Fail to change the second instrument name to the first's one 
        '''
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test2', 'mac': '12:34:56:78:90:AC', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AC', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x01 | 0x40)

    @inlineCallbacks
    def test_failRegisterNew(self):
        '''
        Fail to register a second insrument with diffrenet MAC but same name
        '''
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AC', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x80)

    @inlineCallbacks
    def test_failChangeNameConstantOk(self):
        '''
        Fail to change the second instrument name to the first's one
        but changes constant ok.
        '''
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test2', 'mac': '12:34:56:78:90:AC', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AC', 'calib': 18.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x01 | 0x04 | 0x40)