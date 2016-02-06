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

#--------------------
# System wide imports
# -------------------

import datetime


# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks
from twisted.logger         import Logger

#--------------
# local imports
# -------------

from .utils import Table,  UNKNOWN

# ----------------
# Module Constants
# ----------------


# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------

def _populateRepl(transaction, rows):
    '''Dimension initial data loading (replace flavour)'''
    transaction.executemany(
        "INSERT OR REPLACE INTO time_t VALUES(?,?,?,?,?)", rows)

def _populateIgn(transaction, rows):
    '''Dimension initial data loading (ignore flavour)'''
    transaction.executemany(
        "INSERT OR IGNORE INTO time_t VALUES(?,?,?,?,?)", rows)

# ============================================================================ #
#                               TIME OF DAY TABLE (DIMENSION)
# ============================================================================ #

class TimeOfDay(Table):
    
    ONE         = datetime.timedelta(minutes=1)
    START_TIME  = datetime.datetime(year=1900,month=1,day=1,hour=0,minute=0)
    END_TIME    = datetime.datetime(year=1900,month=1,day=1,hour=23,minute=59)

    def __init__(self, pool):
        '''Create and Populate the SQlite Time of Day Table'''
        Table.__init__(self, pool)



    def table(self):
        '''
        Create the SQLite Time of Day table.
        Returns a Deferred.
        '''
        log.info("Creating Time of Day Table if not exists")
        return self.pool.runOperation(
            '''
            CREATE TABLE IF NOT EXISTS time_t
            (
            time_id        INTEGER PRIMARY KEY, 
            time           TEXT,
            hour           INTEGER,
            minute         INTEGER,
            day_fraction   REAL
            );
            '''
        )



    def populate(self, replace):
        '''
        Populate the SQLite Time Table.
        Retuens a Deferred.
        '''
        if replace:
            log.info("Replacing Time Table data")
            return self.pool.runInteraction( _populateRepl, self.rows() )
        else:
            log.info("Populating Time Table if empty")
            return self.pool.runInteraction( _populateIgn, self.rows() )

    # --------------
    # Helper methods
    # --------------

    
    def rows(self):
        '''Generate a list of rows to inject into the table'''
        time = TimeOfDay.START_TIME
        # Starts with the Unknown value
        timeList = [
            (
                -1,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
            )
        ]
        while time <= TimeOfDay.END_TIME:
            timeList.append(
                (
                    time.hour*100+time.minute, # Key
                    time.strftime("%H:%M"),    # SQLite time string
                    time.hour,            # hour
                    time.minute,          # minute
                    (time.hour*60+time.minute) / (24*60.0), # fraction of day
                )
            )
            time = time + TimeOfDay.ONE
        return timeList


