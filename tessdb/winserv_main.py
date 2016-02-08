# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import sys
import argparse
import errno

import win32serviceutil
import win32event
import servicemanager  
import win32api

import win32service
import win32con
import win32evtlogutil

# ---------------
# Twisted imports
# ---------------

#from twisted.internet import win32eventreactor
#win32eventreactor.install()

from twisted.internet import reactor
from twisted.logger import Logger, LogLevel

#--------------
# local imports
# -------------

import tessdb.logger

from .  import __version__
from tessdb.config import VERSION_STRING, cmdline, loadCfgFile
from tessdb.application import TESSApplication

# ----------------
# Module constants
# ----------------

# Custom Widnows service control in the range of [128-255]
SERVICE_CONTROL_RELOAD = 128

# -----------------------
# Module global variables
# -----------------------

log = Logger('tessdb')


class WindowsService(win32serviceutil.ServiceFramework):
	"""
	Windows service for the EMA database.
	"""
	_svc_name_                = "tessdb"
	_svc_display_name_   = "TESS database {0}".format( __version__)
	_svc_description_        = "An MQTT Client for TESS that stores data into a SQLite database"

	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		self.stop    = win32event.CreateEvent(None, 0, 0, None)
		self.reload  = win32event.CreateEvent(None, 0, 0, None)
		self.pause  = win32event.CreateEvent(None, 0, 0, None)
		self.resume = win32event.CreateEvent(None, 0, 0, None)

	def SvcStop(self):
		'''Service Stop entry point'''
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		log.info("Stopping emadb {version} Windows service", version= __version__ )
		reactor.callFromThread(reactor.stop)
		logger.sysLogInfo("Stopping emadb %s Windows service" % __version__ )
		win32event.SetEvent(self.stop)

	def SvcPause(self):
		'''Service Pause entry point'''
		self.ReportServiceStatus(win32service.SERVICE_PAUSE_PENDING)
		log.info("Pausing  emadb {version} Windows service",  version=__version__ )
		logger.sysLogInfo("Pausing emadb %s Windows service" % __version__ )
		win32event.SetEvent(self.pause)
		
	def SvcContinue(self):
		'''Service Continue entry point'''
		self.ReportServiceStatus(win32service.SERVICE_CONTINUE_PENDING)
		log.info("Resuming emadb %s Windows service", __version__  )
		logger.sysLogInfo("Resuming emadb %s Windows service" % __version__ )
		win32event.SetEvent(self.resume)

	def SvcOtherEx(self, control, event_type, data):
		'''Implements a Reload functionality as a  service custom control'''
		if control == SERVICE_CONTROL_RELOAD:
			self.SvcDoReload()
		else:
			self.SvcOther(control)


	def SvcDoReload(self):
		logger.sysLogInfo("reloading emadb service")
		win32event.SetEvent(self.reload)


	def SvcDoRun(self):
		'''Service Run entry point'''
		logger.sysLogInfo("Starting tessdb %s Windows service {0}".format( __version__ ))
		# initialize your services here
		# Read the command line arguments and config file options
		cmdline_opts = cmdline()
		if cmdline_opts.config:
			config_opts  = loadCfgFile(cmdline_opts.config)
		else:
			config_opts = None

		# Start the logging subsystem
		startLogging(console=False, filepath=config_opts['log']['path'])

		sysLogInfo("Starting {0}".format(VERSION_STRING))
		application = TESSApplication(cmdline_opts, config_opts)
		application.run()
		win32event.WaitForSingleObject(self.hWaitStop,win32event.INFINITE)
		logger.sysLogInfo("tessdb %s Windows service stopped {0}".format( __version__ ))

     
def ctrlHandler(ctrlType):
    return True

if not servicemanager.RunningAsService():   
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
    win32serviceutil.HandleCommandLine(WindowsService)
