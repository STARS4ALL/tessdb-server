# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import
import sys

# ---------------
# Twisted imports
# ---------------

from twisted.internet import reactor
from twisted.application.service import IService

#--------------
# local imports
# -------------

from tessdb  import __version__
from tessdb.application import application
from tessdb.logger      import sysLogInfo

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------

# MAIN CODE

sysLogInfo("Starting {0} {1} Linux service".format(IService(application).name, __version__ ))
IService(application).startService()
reactor.run()
sysLogInfo("{0} {1} Linux service stopped".format(IService(application).name, __version__ ))
sys.exit(0)