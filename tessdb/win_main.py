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

from twisted.logger import Logger
from twisted.internet import reactor

#--------------
# local imports
# -------------

from .logger import sysLogInfo,  startLogging
from .config import VERSION_STRING, cmdline, loadCfgFile
from .application import TESSApplication

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------


# Read the command line arguments and config file options
cmdline_opts = cmdline()
if cmdline_opts.config:
	config_opts  = loadCfgFile(cmdline_opts.config)
else:
	config_opts = None


# Start the logging subsystem
startLogging(console=cmdline_opts.console, filepath=config_opts['log']['path'])

sysLogInfo("Starting {0}".format(VERSION_STRING))
application = TESSApplication(config_opts['log']['path'], config_opts)
application.start()
reactor.run()
sysLogInfo("Stopped {0}".format(VERSION_STRING))
