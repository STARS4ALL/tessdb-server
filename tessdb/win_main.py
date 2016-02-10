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
config_file = cmdline_opts.config
if config_file:
	config_opts  = loadCfgFile(config_file)
else:
	config_opts = None

log_file = config_opts['log']['path']
# Start the logging subsystem
startLogging(console=cmdline_opts.console, filepath=log_file)

sysLogInfo("Starting {0}".format(VERSION_STRING))
application = TESSApplication(config_file, config_opts)
application.start()
reactor.run()
sysLogInfo("Stopped {0}".format(VERSION_STRING))
