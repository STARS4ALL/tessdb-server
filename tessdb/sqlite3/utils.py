# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2016 Rafael Gonzalez.
#
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import json
import datetime
import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.internet.defer import inlineCallbacks, returnValue, succeed
from twisted.logger   import Logger
    
#--------------
# local imports
# -------------

# ----------------
# Module Constants
# ----------------

UNKNOWN       = 'Unknown'
START_TIME    = "2016-01-01 00:00:00"
INFINITE_TIME = "2999-12-31 23:59:59"
EXPIRED       = "Expired"
CURRENT       = "Current"
TSTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------

def roundDateTime(ts):
   '''Round a timestamp to the nearest minute'''
   tsround = ts + datetime.timedelta(minutes=0.5)
   time_id = tsround.hour*100   + tsround.minute
   date_id = tsround.year*10000 + tsround.month*100 + tsround.day
   return date_id, time_id


# caveat: this is a blocking I/O operation, but since we are generating
# the schema, it doesn't make any difference.
def fromJSON(file_path, default_var):
    '''
    Read pre-populated JSON data from a file
    '''
    lines = []
    if not os.path.exists(file_path):
        log.warn("No JSON file found in {file}", file=file_path)
        log.warn("loading defaults {var!s}.", var=default_var)
        return default_var
    log.info("loading from existing file {file}", file=file_path)
    with open(file_path,'r') as fd:
        for line in fd:
            if not line.startswith('#'):
                lines.append(line)
    return  json.loads('\n'.join(lines))

def utcnoon():
    '''Returns the ephem Date object at today's noon'''
    return ephem.Date(datetime.datetime.utcnow().replace(hour=12, minute=0, second=0,microsecond=0))


def utcnow():
    '''Returns now's ephem Date object '''
    return ephem.Date(datetime.datetime.utcnow())


def isDaytime(sunrise, sunset, now):
    '''
    Test if it is daytime for a given observer
    'sunrise' and 'sunset' are timestamp strings.
    'now' is a datetime.datetime object or timestamp string
    '''
    # sunrise, sunset comes from the DB and are UNICODE strings
    # epehm doesn't like unicode strings
    return  ephem.Date(str(sunrise)) < ephem.Date(now)  < ephem.Date(str(sunset))

# ----------------------
# Module Utility Classes
# ----------------------

class Table(object):
    '''Table object with generic template method'''

    def __init__(self, pool):
        '''Create a table and stores a pool reference to the database'''
        self.pool = pool

    def indices(self):
        '''
        Default index creation implementation for those tables
        that do not create indices
        '''
        return succeed(None)

    def views(self):
        '''
        Create views for outrigger dimensions if neccessary
        '''
        return succeed(None)

    @inlineCallbacks
    def schema(self, json_dir, replace):
        '''
        Generates a table, taking an open data connection
        and a replace flag.
        '''
        self.json_dir = json_dir
        yield self.table()
        yield self.indices()
        yield self.views()
        yield self.populate(replace)
