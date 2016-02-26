# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2016 Rafael Gonzalez.
#
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

def julian_day(date):
    '''Returns the Julian day number of a date at noon.'''
    a = (14 - date.month)//12
    y = date.year + 4800 - a
    m = date.month + 12*a - 3
    return date.day + ((153*m + 2)//5) + 365*y + y//4 - y//100 + y//400 - 32045

def _populateRepl(transaction, rows):
    '''Dimension initial data loading (replace flavour)'''
    transaction.executemany(
        "INSERT OR REPLACE INTO date_t VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        
def _populateIgn(transaction, rows):
    '''Dimension initial data loading (ignore flavour)'''
    transaction.executemany(
        "INSERT OR IGNORE INTO date_t VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

# ============================================================================ #
#                               DATE TABLE (DIMENSION)
# ============================================================================ #
     
class Date(Table):

    ONE         = datetime.timedelta(days=1)

    def __init__(self, pool):
        '''Create and Populate the SQLite Date Table'''
        Table.__init__(self, pool)

    @inlineCallbacks
    def schema(self, date_fmt, year_start, year_end, replace):
        '''
        Overrides generic schema mehod with custom params.
        '''
        self.replace = replace
        self.__fmt   = date_fmt
        self.__start = datetime.date(year_start,1,1)
        self.__end   = datetime.date(year_end,12,31)
        yield self.table()
        yield self.populate(None, replace)

      
    def table(self):
        '''
        Create the SQLite Date Table
        Returns a Deferred
        '''
        log.info("Creating Date Table if not exists")
        return self.pool.runOperation(
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


    def populate(self, json_dir, replace):
        '''
        Populate the SQLite Date Table.
        Returns a Deferred
        '''
        if replace:
            log.info("Replacing Date Table data")
            return self.pool.runInteraction( _populateRepl, self.rows() )
        else:
            log.info("Populating Date Table if empty")
            return self.pool.runInteraction( _populateIgn, self.rows() )


    # --------------
    # Helper methods
    # --------------

    def rows(self):
        '''Generate a list of rows to inject into the table'''
        date = self.__start
        dateList = [
            (
                -1,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
                UNKNOWN, 
                UNKNOWN,
                UNKNOWN,
                UNKNOWN,
            )
        ]
        while date <= self.__end:
            dateList.append(
                (
                    date.year*10000+date.month*100+date.day, # Key
                    str(date),            # SQLite date string
                    date.strftime(self.__fmt),  # date string
                    date.day,             # day of month
                    date.strftime("%j"),  # day of year
                    julian_day(date)+0.5,     # At midnight (+ or - ?????)
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

