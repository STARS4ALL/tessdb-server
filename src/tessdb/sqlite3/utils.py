# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2016 Rafael Gonzalez.
#
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import os
import json
import datetime
import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
    
#--------------
# local imports
# -------------

# ----------------
# Module Constants
# ----------------

UNKNOWN       = 'Unknown'
START_TIME    = "2016-01-01T00:00:00"
INFINITE_TIME = "2999-12-31T23:59:59"
EXPIRED       = "Expired"
CURRENT       = "Current"
TSTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
# For sunset/sunrise in circumpolar sites
NEVER_UP      = "Never Up"
ALWAYS_UP     = "Always Up"

# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------

def roundDateTime(ts, secs_resol):
    '''Round a timestamp to the nearest minute'''
    if secs_resol > 1:
        tsround = ts + datetime.timedelta(seconds=0.5*secs_resol)
    else:
        tsround = ts
    time_id = tsround.hour*10000 + tsround.minute*100 + tsround.second
    date_id = tsround.year*10000 + tsround.month *100 + tsround.day
    return date_id, time_id


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
    # pyephem doesn't like unicode strings
    sunrise = str(sunrise)
    sunset = str(sunset)
    if sunrise == NEVER_UP:
        return False
    if sunrise == ALWAYS_UP:
        return True
    sunrise = ephem.Date(sunrise)
    sunset = ephem.Date(sunset)
    now = ephem.Date(now)
    # In locations near Grenwich: (prev) sunrise < (next) sunset
    # In location far away from Greenwich: (prev) sunset < (next) sunrise
    if sunrise < sunset:
        return  sunrise < now  < sunset
    else: 
        return not (sunset < now  < sunrise)

# ----------------------
# Module Utility Classes
# ----------------------

class Table(object):
    '''Table object with generic template method'''

    def __init__(self, connection):
        '''Create a table and stores a synchronous reference to the database
        for initialization purposes'''
        self.connection = connection
        # Asynchronous coonection pool se to None at this stage
        self.pool = None

    def indices(self):
        '''
        Default index creation implementation for those tables
        that do not create indices
        '''
        return

    def views(self):
        '''
        Create views for outrigger dimensions if neccessary
        '''
        return

    def schema(self):
        '''
        Generates a table, taking an open data connection
        and a replace flag.
        '''
        self.table()
        self.indices()
        self.views()
        self.populate()
