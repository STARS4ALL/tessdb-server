# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys
import signal

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

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

# SIGNAL HANDLERS

def sigreload(signum, frame):
   '''
   Signal handler (SGUHUP only)
   '''
   TESSApplication.instance.sigreload = True
   
def sigpause(signum, frame):
   '''
   Signal handler (SIGUSR1 only)
   '''
   TESSApplication.instance.sigpause = True

def sigresume(signum, frame):
   '''
   Signal handler (SIGUSR2 only)
   '''
   TESSApplication.instance.sigresume = True



# Read the command line arguments and config file options
cmdline_opts = cmdline()
if cmdline_opts.config:
	config_opts  = loadCfgFile(cmdline_opts.config)
else:
	config_opts = None

# Install signal handlers
signal.signal(signal.SIGHUP,  sigreload)
signal.signal(signal.SIGUSR1, sigpause)
signal.signal(signal.SIGUSR2, sigresume)

# Start the logging subsystem
startLogging(console=cmdline_opts.console, filepath=config_opts['log']['path'])

sysLogInfo("Starting {0}".format(VERSION_STRING))
application = TESSApplication(filepath, config_opts)
application.run()
#service  = TESS_Service(config_opts)
sysLogInfo("Stopped {0}".format(VERSION_STRING))
