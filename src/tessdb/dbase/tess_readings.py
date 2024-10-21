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

import sqlite3

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks
from twisted.logger import Logger

# --------------
# local imports
# -------------

from . import NAMESPACE
from .utils import roundDateTime


# ----------------
# Module Constants
# ----------------

IMPOSSIBLE_TEMP = -273.15
IMPOSSIBLE_SIGNAL_STRENGTH = 99

INSERT_READING_SQL = """
    INSERT INTO tess_readings_t (
        date_id,
        time_id,
        tess_id,
        location_id,
        observer_id,
        units_id,
        sequence_number,
        frequency,               
        magnitude,              
        box_temperature,    
        sky_temperature,    
        azimuth,            
        altitude,           
        longitude,          
        latitude,           
        elevation,           
        signal_strength,     
        hash       
    ) VALUES (
        :date_id,
        :time_id,
        :tess_id,
        :location_id,
        :observer_id,
        :units_id,
        :seq,
        :freq1,               
        :mag1,                        
        :tamb,    
        :tsky,    
        :az,            
        :alt,           
        :long,          
        :lat,           
        :height,           
        :wdBm,     
        :hash
    )
"""


INSERT_READING4C_SQL = """
    INSERT INTO tess_readings4c_t (
        date_id,
        time_id,
        tess_id,
        location_id,
        observer_id,
        units_id,
        sequence_number,
        freq1,               
        mag1,              
        freq2,              
        mag2,               
        freq3,              
        mag3,               
        freq4,              
        mag4,               
        box_temperature,    
        sky_temperature,    
        azimuth,            
        altitude,           
        longitude,          
        latitude,           
        elevation,           
        signal_strength,     
        hash       
    ) VALUES (
        :date_id,
        :time_id,
        :tess_id,
        :location_id,
        :observer_id,
        :units_id,
        :seq,
        :freq1,               
        :mag1,              
        :freq2,              
        :mag2,               
        :freq3,              
        :mag3,               
        :freq4,              
        :mag4,               
        :tamb,    
        :tsky,    
        :az,            
        :alt,           
        :long,          
        :lat,           
        :height,           
        :wdBm,     
        :hash
    )
"""
# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------


def isTESS4C(row):
    return "freq4" in row


# ============================================================================ #
#                   REAL TIME TESS READNGS (PERIODIC SNAPSHOT FACT TABLE)
# ============================================================================ #


class TESSReadings:
    BUFFER_SIZE = 15
    FACTOR = 0.6  # TESS4C Buffer size in peerfentage of TESS-W Buffer size

    def __init__(self, parent):
        """Create the SQLite TESS Readings table"""
        self.parent = parent
        self.pool = None
        self.authFilter = True
        self.resetCounters()
        # Internal buffers to do Block Writes
        self._rows1C = list()
        self._rows4C = list()
        self._tesswSIZE = self.BUFFER_SIZE
        self._tess4cSIZE = max(1, int(self.BUFFER_SIZE * self.FACTOR))

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        """Resets stat counters"""
        self.nreadings = 0
        self.rejNotRegistered = 0
        self.rejNotAuthorised = 0
        self.rejSunrise = 0
        self.rejDuplicate = 0
        self.rejOther = 0

    def getCounters(self):
        """get stat counters"""
        return [
            self.nreadings,
            self.rejNotRegistered,
            self.rejNotAuthorised,
            self.rejSunrise,
            self.rejDuplicate,
            self.rejOther,
        ]

    # ===============
    # OPERATIONAL API
    # ===============

    def setPool(self, pool):
        self.pool = pool

    def setBufferSize(self, n):
        self._tesswSIZE = max(1, n)
        self._tess4cSIZE = max(1, int(n * self.FACTOR))

    def setAuthFilter(self, auth_filter):
        """
        Set filtering Auth
        """
        self.authFilter = auth_filter

    @inlineCallbacks
    def update(self, row):
        """
        Update tess_readings_t with a new row
        Takes care of optional fields
        Returns a Deferred.
        """
        ok = yield self._gatherInfo(row)
        if ok:
            log.debug("Appending {name} reading for DB Write", name=row["name"])
            if isTESS4C(row):
                buf = self._rows4C
                sql = INSERT_READING4C_SQL
                tag = "TESS4C"
                N = self._tess4cSIZE
            else:
                buf = self._rows1C
                sql = INSERT_READING_SQL
                tag = "TESS-W"
                N = self._tesswSIZE
            buf.append(row)
            if len(buf) >= N:
                log.info("Flushing {tag} queue with {len} readings", len=len(buf), tag=tag)
                yield self.flush(buf, sql)

    # ==============
    # Helper methods
    # ==============

    @inlineCallbacks
    def _gatherInfo(self, row):
        now = row["tstamp"]
        self.nreadings += 1
        tess = yield self.parent.tess.findPhotometerByName(row)
        log.debug(
            "TESSReadings.update({log_tag}): Found TESS => {tess!s}",
            tess=tess,
            log_tag=row["name"],
        )
        if not len(tess):
            log.warn(
                "TESSReadings.update(): No TESS {log_tag} registered ! => {row}",
                log_tag=row["name"],
                row=row,
            )
            self.rejNotRegistered += 1
            return False
        (
            tess_id,
            mac_address,
            zp1,
            zp2,
            zp3,
            zp4,
            filter1,
            filter2,
            filter3,
            filter4,
            offset1,
            offset2,
            offset3,
            offset4,
            authorised,
            registered,
            location_id,
            observer_id,
        ) = tess[0]
        authorised = authorised == 1
        # Review authorisation if this filter is enabled
        if self.authFilter and not authorised:
            log.warn(
                "TESSReadings.update({log_tag}): authorised: {value}",
                log_tag=row["name"],
                value=authorised,
            )
            self.rejNotAuthorised += 1
            return False
        row["date_id"], row["time_id"] = roundDateTime(now, self.parent.options["secs_resolution"])
        row["tess_id"] = tess_id
        row["units_id"] = yield self.parent.tess_units.latest(timestamp_source=row["tstamp_src"])
        row["location_id"] = location_id
        row["observer_id"] = observer_id
        row["az"] = row.get("az")
        row["alt"] = row.get("alt")
        row["long"] = row.get("long")
        row["lat"] = row.get("lat")
        row["height"] = row.get("height")
        row["hash"] = row.get("hash")
        # TESS4C Early prototypes did not provide any temperature
        row["tamb"] = row.get("tamb", IMPOSSIBLE_TEMP)
        row["tsky"] = row.get("tsky", IMPOSSIBLE_TEMP)
        # TESSTRACTOR software emulation do not provide received signal strength
        row["wdBm"] = row.get("wdBm", IMPOSSIBLE_SIGNAL_STRENGTH)
        log.debug(
            "TESSReadings.update({log_tag}): About to write to DB {row!s}",
            log_tag=row["name"],
            row=row,
        )
        return True

    def database_write(self, rows, sql):
        """
        Append row in one of the readings table where rows may be
        - a single row (a dict) or
        - a sequence of rows (sequence or tuple of dicts)
        Returns a Deferred
        """

        def _database_write(txn):
            log.debug("{sql} <= {rows}", sql=sql, rows=rows)
            if type(rows) in (list, tuple):
                txn.executemany(sql, rows)
            else:
                txn.execute(sql, rows)

        return self.pool.runInteraction(_database_write)

    @inlineCallbacks
    def flush(self, rows, sql):
        try:
            yield self.database_write(rows, sql)
        except sqlite3.IntegrityError:
            log.warn("SQL Integrity error in block write. Looping one by one ...")
            for row in rows:
                try:
                    yield self.database_write(row, sql)
                except sqlite3.IntegrityError:
                    log.error("Discarding row by SQL Integrity error: {row}", row=row)
                    self.rejDuplicate += 1
                except Exception as e:
                    log.error(
                        "Discarding row by other SQL error. Exception {excp}, row: {row}",
                        excp=e,
                        row=row,
                    )
                    self.rejOther += 1
        except Exception as e:
            log.error(
                "TESSReadings.update(): exception {excp!s}. Looping one by one ...",
                excp=e,
            )
            for row in rows:
                try:
                    yield self.database_write(row, sql)
                except Exception as e:
                    log.error(
                        "Discarding row by other SQL error. Exception {excp}, row: {row}",
                        excp=e,
                        row=row,
                    )
                    self.rejOther += 1
        finally:
            rows.clear()
