# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

# ---------------
# Twisted imports
# ---------------

from twisted.enterprise import adbapi

#--------------
# local imports
# -------------

from .date          import Date
from .time          import TimeOfDay
from .tess_units    import TESSUnits
from .location      import Location
from .tess          import TESS
from .tess_readings import TESSReadings

# ----------------
# Global Functions
# ----------------

def getPool(*args, **kargs):
	'''Get connetion pool for sqlite3 driver'''
   	kargs['check_same_thread']=False
   	return adbapi.ConnectionPool("sqlite3", *args, **kargs)


__all__ = [
	getPool, Date, TimeOfDay, TESSUnits, Location, TESS, TESSReadings
]