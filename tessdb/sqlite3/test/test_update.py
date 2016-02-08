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


class UpdateUnregisteredTestCase(unittest.TestCase):

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove('tesoro.db')
        except OSError as e:
            pass
        self.db = DBase("tesoro.db")
        yield self.db.schema('foo', '%Y/%m/%d', 2015, 2026, replace=False)

    def tearDown(self):
        self.db.pool.close()
    
    @inlineCallbacks
    def test_updateWithNoInstrument(self):
        '''
        Test insert reading with no instrument registered.
        It should not be inserted
        '''
        row = { 'name': 'test1', 'seqno': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12}
        res = yield self.db.update(row)
        self.assertEqual(res, 0x00)

class UpdateRegisteredTestCase(unittest.TestCase):

    @inlineCallbacks
    def setUp(self):
        try:
            os.remove('tesoro.db')
        except OSError as e:
            pass
        self.db = DBase("tesoro.db")
        yield self.db.schema('foo', '%Y/%m/%d', 2015, 2026, replace=False)
        row = { 'name': 'test1', 'mac': '12:34:56:78:90:AB', 'calib': 10.0}
        res = yield self.db.register(row)
        self.assertEqual(res, 0x00)

    def tearDown(self):
        self.db.pool.close()
    
    @inlineCallbacks
    def test_updateWithInstrument(self):
        '''
        Test insert a reading with instrument registered.
        It should be inserted
        '''
        row = { 'name': 'test1', 'seqno': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12}
        res = yield self.db.update(row)
        self.assertEqual(res, 0x01)
      
    @inlineCallbacks
    def test_updateTooFast(self):
        '''
        Test fast inserting two readings with instrument registered.
        The first one should be inserted, the second one not.
        '''
        row = { 'name': 'test1', 'seqno': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12}
        res = yield self.db.update(row)
        self.assertEqual(res, 0x01)
        row = { 'name': 'test1', 'seqno': 1, 'freq': 1000.01, 'mag':12.0, 'tamb': 0, 'tsky': -12}
        res = yield self.db.update(row)
        self.assertEqual(res, 0x40)
