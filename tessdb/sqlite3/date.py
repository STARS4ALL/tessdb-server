# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2016 Rafael Gonzalez.
#
# ----------------------------------------------------------------------

from __future__ import division, absolute_import

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

from tessdb.sqlite3.utils import Table,  UNKNOWN

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

def julian_day(date):
    '''Returns the Julian day number of a date at 0h UTC.'''
    a = (14 - date.month)//12
    y = date.year + 4800 - a
    m = date.month + 12*a - 3
    return (date.day + ((153*m + 2)//5) + 365*y + y//4 - y//100 + y//400 - 32045) - 0.5


# ============================================================================ #
#                               DATE TABLE (DIMENSION)
# ============================================================================ #
     
class Date(Table):

    ONE         = datetime.timedelta(days=1)

    def __init__(self, connection):
        '''Create and Populate the SQLite Date Table'''
        Table.__init__(self, connection)

    def schema(self, date_fmt, year_start, year_end):
        '''
        Overrides generic schema mehod with custom params.
        '''
        self.__fmt   = date_fmt
        self.__start = datetime.date(year_start,1,1)
        self.__end   = datetime.date(year_end,12,31)
        self.table()
        self.populate()

      
    def table(self):
        '''
        Create the SQLite Date Table
        '''
        log.info("Creating Date Table if not exists")
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS date_t
            (
            date_id        INTEGER PRIMARY KEY, 
            sql_date       TEXT, 
            date           TEXT,
            day            INTEGER,
            day_year       INTEGER,
            julian_day     REAL,
            weekday        TEXT,
            weekday_abbr   TEXT,
            weekday_num    INTEGER,
            month_num      INTEGER,
            month          TEXT,
            month_abbr     TEXT,
            year           INTEGER
            );
            '''
        )
        self.connection.commit()


    def populate(self):
        '''
        Populate the SQLite Date Table.
        Returns a Deferred
        '''
        log.info("Populating/Replacing Date Table data")
        self.connection.executemany( 
            "INSERT OR REPLACE INTO date_t VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            self.rows() 
        )
        self.connection.commit()


    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject into the table'''
        date = self.__start
        dateList = []
        while date <= self.__end:
            dateList.append(
                (
                    date.year*10000+date.month*100+date.day, # Key
                    str(date),            # SQLite date string
                    date.strftime(self.__fmt),  # date string
                    date.day,             # day of month
                    date.strftime("%j"),  # day of year
                    julian_day(date),     # At midnight
                    date.strftime("%A"),      # weekday name
                    date.strftime("%a"),      # abbreviated weekday name
                    int(date.strftime("%w")), # weekday number (0=Sunday)
                    date.month,               # Month Number
                    date.strftime("%B"),      # Month Name
                    date.strftime("%b"),      # Month Abbr. Name
                    date.year,                # Year
                )
            )
            date = date + Date.ONE
        return dateList

