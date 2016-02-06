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
from .dbase import DBase

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------



@inlineCallbacks
def main():
	startLogging()
	dbase = DBase(sys.argv[1])
	yield dbase.schema('config', '%Y/%m/%d', 2015, 2026, replace=False)
	reactor.stop()

main()
reactor.run()
