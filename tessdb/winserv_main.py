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

from .logger import sysLogInfo, startLogging

from .  import __version__
from .config import VERSION_STRING, cmdline, loadCfgFile
from .application import TESSApplication

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
		
		self.config_opts  = loadCfgFile(r"C:\tessdb\config\config.ini")
		startLogging(console=False, filepath=self.config_opts['log']['path'])
		log.info("Creating {cls} object instance",cls="WindowsService")


	def SvcStop(self):
		'''Service Stop entry point'''
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		reactor.callFromThread(reactor.stop)
		sysLogInfo("Stopping  tessdb {0} Windows service".format( __version__ ))

	def SvcPause(self):
		'''Service Pause entry point'''
		self.ReportServiceStatus(win32service.SERVICE_PAUSE_PENDING)
		sysLogInfo("Pausing  tessdb {0} Windows service".format( __version__ ))
		win32event.SetEvent(self.pause)
		
	def SvcContinue(self):
		'''Service Continue entry point'''
		self.ReportServiceStatus(win32service.SERVICE_CONTINUE_PENDING)
		sysLogInfo("Resuming tessdb {0} Windows service".format( __version__ ))
		win32event.SetEvent(self.resume)

	def SvcOtherEx(self, control, event_type, data):
		'''Implements a Reload functionality as a  service custom control'''
		if control == SERVICE_CONTROL_RELOAD:
			self.SvcDoReload()
		else:
			self.SvcOther(control)


	def SvcDoReload(self):
		sysLogInfo("reloading tessdb service")
		win32event.SetEvent(self.reload)


	def SvcDoRun(self):
		'''Service Run entry point'''
		sysLogInfo("Starting tessdb {0} Windows service {0}".format( __version__ ))
		# initialize your services here
		log.info("Starting windows service {service}", service=VERSION_STRING)
		sysLogInfo("Starting {0}".format(VERSION_STRING))
		application = TESSApplication(r"C:\tessdb\config\config.ini", self.config_opts)
		application.run(installSignalHandlers=0)
		sysLogInfo("tessdb Windows service stopped {0}".format( __version__ ))

     
def ctrlHandler(ctrlType):
    return True

if not servicemanager.RunningAsService():   
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
    win32serviceutil.HandleCommandLine(WindowsService)
