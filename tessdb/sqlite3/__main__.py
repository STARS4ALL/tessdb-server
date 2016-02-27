# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys

# ---------------
# Twisted imports
# ---------------

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.logger   import LogLevel

#--------------
# local imports
# -------------

from ..logger import startLogging
from .dbase import getPool
from .date          import Date
from .time          import TimeOfDay
from .tess_units    import TESSUnits
from .location      import Location
from .tess          import TESS
from .tess_readings import TESSReadings

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# ----------------
# Module functions
# ----------------


@inlineCallbacks
def main():
    startLogging()
    pool = getPool(sys.argv[1])
    
    tess           = TESS(pool)
    tess_units     = TESSUnits(pool)
    tess_readings  = TESSReadings(pool, parent=None)
    tess_locations = Location(pool)
    date           = Date(pool)
    timeOfDay      = TimeOfDay(pool)

    yield date.schema(date_fmt='%Y/%m/%d', year_start=2016, year_end=2026, replace=True)
    yield timeOfDay.schema(json_dir='etc/tessdb/config', replace=True)
    yield tess_locations.schema(json_dir='etc/tessdb/config', replace=True)
    yield tess.schema(json_dir='etc/tessdb/config', replace=True)
    yield tess_units.schema(json_dir='etc/tessdb/config', replace=True)
    yield tess_readings.schema(json_dir='etc/tessdb/config', replace=True)

    reactor.stop()

main()
reactor.run()
