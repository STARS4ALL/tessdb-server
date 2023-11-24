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

from __future__ import division, absolute_import

import datetime


# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks
from twisted.logger         import Logger

#--------------
# local imports
# -------------

from tessdb.sqlite3.utils import Table

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


# ============================================================================ #
#                               TIME OF DAY TABLE (DIMENSION)
# ============================================================================ #

class TimeOfDay(Table):
    
   
    START_TIME  = datetime.datetime(year=1900,month=1,day=1,hour=0,minute=0,second=0)
    END_TIME    = datetime.datetime(year=1900,month=1,day=1,hour=23,minute=59,second=59)

    def __init__(self, connection, secs_resol):
        '''Create and Populate the SQlite Time of Day Table'''
        Table.__init__(self, connection)
        self.secs_resol = secs_resol
        self.ONE        = datetime.timedelta(seconds=secs_resol)

    def table(self):
        '''
        Create the SQLite Time of Day table.
        '''
        log.info("Creating Time of Day Table if not exists")
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS time_t
            (
            time_id        INTEGER PRIMARY KEY, 
            time           TEXT,
            hour           INTEGER,
            minute         INTEGER,
            second         INTEGER,
            day_fraction   REAL
            );
            '''
        )
        self.connection.commit()


    def populate(self):
        '''
        Populate the SQLite Time Table.
        '''
        log.info("Populating/Replacing Time Table data")
        self.connection.executemany( 
            "INSERT OR REPLACE INTO time_t VALUES(?,?,?,?,?,?)", 
            self.rows() 
        )
        self.connection.commit()

    # --------------
    # Helper methods
    # --------------

    
    def rows(self):
        '''Generate a list of rows to inject into the table'''
        time = TimeOfDay.START_TIME
        # Starts with the Unknown value
        timeList = []
        while time <= TimeOfDay.END_TIME:
            timeList.append(
                (
                    time.hour*10000+time.minute*100+time.second, # Key
                    time.strftime("%H:%M:%S"), # SQLite time string
                    time.hour,                 # hour
                    time.minute,               # minute
                    time.second,               # second
                    (time.hour*3600+time.minute*60+time.second) / (24*60*60.0), # fraction of day
                )
            )
            time = time + self.ONE
        return timeList


