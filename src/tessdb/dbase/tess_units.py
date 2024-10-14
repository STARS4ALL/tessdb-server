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

# --------------------
# System wide imports
# -------------------


# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks
from twisted.logger import Logger

# --------------
# local imports
# -------------

from . import NAMESPACE

# ----------------
# Module Constants
# ----------------


# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace=NAMESPACE)


# ------------------------
# Module Utility Functions
# ------------------------


# ============================================================================ #
#                               UNITS TABLE (DIMENSION)
# ============================================================================ #

# This is what is left after an extensive refactoring but still maintianing the class


class TESSUnits:
    def __init__(self):
        # Cached row ids
        self._id = {}
        self._id["Publisher"] = None
        self._id["Subscriber"] = None
        self.pool = None

    # ===============
    # OPERATIONAL API
    # ===============

    def setPool(self, pool):
        self.pool = pool

    @inlineCallbacks
    def latest(self, timestamp_source="Subscriber", reading_source="Direct"):
        def queryLatest(dbpool, timestamp_source):
            row = {
                "timestamp_source": timestamp_source,
                "reading_source": reading_source,
            }
            return dbpool.runQuery(
                """
                SELECT units_id FROM tess_units_t
                WHERE timestamp_source == :timestamp_source
                AND reading_source == :reading_source
                """,
                row,
            )

        if self._id.get(timestamp_source) is None:
            row = yield queryLatest(self.pool, timestamp_source)
            self._id[timestamp_source] = row[0][0]
        return self._id[timestamp_source]
