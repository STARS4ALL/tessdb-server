# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import ephem
import datetime
import math

# ---------------
# Twisted imports
# ---------------

#--------------
# local imports
# -------------

def utcnoon():
    '''Returns the ephem Date object at today's noon'''
    return ephem.Date(datetime.datetime.utcnow().replace(hour=12, minute=0, second=0,microsecond=0))


def utcnow():
    '''Returns now's ephem Date object '''
    return ephem.Date(datetime.datetime.utcnow())

def isDay(observer, now=utcnow()):
    '''
    Test if it is daytime for a given observer
    '''
    sunset, sunrise = sunLimits(observer)
    return sunrise < now < sunset


def sunLimits(locations, sun, noon, horizon='0'):
    '''
    Calculates sunrise/sunset for a given list of locations.
    Ideally, it needs only to be computed once, after midnight.
    'locations' is a list of tuples (id,longitude,latitude,elevation)
    Returns a list of dictionaries with the following keys:
    - id
    - 'sunrise'
    - 'sunset'
    '''
    observer = ephem.Observer()
    observer.pressure  = 0      # disable refraction calculation
    observer.horizon   = horizon
    observer.date      = noon
    rows = []
    for location in locations:
        observer.lon       = math.radians(location[1])
        observer.lat       = math.radians(location[2])
        observer.elevation = location[3]
        row = {}
        row['id']      = location[0]
        row['sunrise'] = str(observer.previous_rising(sun, use_center=True))
        row['sunset']  = str(observer.next_setting(sun, use_center=True))
        rows.append(row)
    return rows