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

# ---------------
# Twisted imports
# ---------------

from twisted.trial import unittest
from twisted.logger import Logger

# --------------
# local imports
# -------------

from tessdb.error import ReadingKeyError, ReadingTypeError


log = Logger()


# tessdb.logger.startLogging(sys.stdout, LogLevel.debug)
class ExceptionTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def f1(self):
        raise ReadingKeyError(set(["name", "seq"]))

    def f2(self):
        raise ReadingTypeError("name", str, type(1))

    def f3(self):
        raise ReadingTypeError("az", float, type("a"))

    def f4(self):
        raise ReadingTypeError("seq", int, type(3.0))

    def test_ReadingKeyError(self):
        self.assertRaises(ReadingKeyError, self.f1)
        try:
            self.f1()
        except ReadingKeyError as e:
            log.error("{excp}", excp=e)

    def test_ReadingTypeError(self):
        self.assertRaises(ReadingTypeError, self.f2)
        self.assertRaises(ReadingTypeError, self.f3)
        self.assertRaises(ReadingTypeError, self.f4)
        try:
            self.f2()
        except ReadingTypeError as e:
            log.error("{excp}", excp=e)
        try:
            self.f3()
        except ReadingTypeError as e:
            log.error("{excp}", excp=e)
        try:
            self.f4()
        except ReadingTypeError as e:
            log.error("{excp}", excp=e)
