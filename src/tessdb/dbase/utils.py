# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2016 Rafael Gonzalez.
#
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
    
#--------------
# local imports
# -------------

from . import NAMESPACE

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

log = Logger(namespace=NAMESPACE)

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
