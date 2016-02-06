# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
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
application = TESSApplication(cmdline_opts, config_opts)
application.run()
#service  = TESS_Service(config_opts)
sysLogInfo("Stopped {0}".format(VERSION_STRING))
