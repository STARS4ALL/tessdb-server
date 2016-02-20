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

def utcnow():
    '''Returns now's ephem Date object '''
    return ephem.Date(datetime.datetime.utcnow())

def isDay(observer, now=utcnow()):
    '''
    Test if it is daytime for a given observer
    '''
    sunset, sunrise = sunLimits(observer)
    return sunrise < now < sunset

