# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

# ---------------
# Twisted imports
# ---------------

from twisted.enterprise import adbapi

#--------------
# local imports
# -------------

from tessdb.sqlite3.date          import Date
from tessdb.sqlite3.time          import TimeOfDay
from tessdb.sqlite3.tess_units    import TESSUnits
from tessdb.sqlite3.location      import Location
from tessdb.sqlite3.tess          import TESS
from tessdb.sqlite3.tess_readings import TESSReadings

# ----------------
# Global Functions
# ----------------

def getPool(*args, **kargs):
    '''Get connetion pool for sqlite3 driver'''
    kargs['check_same_thread'] = False
    return adbapi.ConnectionPool("sqlite3", *args, **kargs)


__all__ = [
    "getPool", 
    "Date", 
    "TimeOfDay", 
    "TESSUnits", 
    "Location", 
    "TESS", 
    "TESSReadings"
]