# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

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

from tessdb  import __version__

from tessdb.logger               import sysLogInfo
from tessdb.application          import application
from tessdb.service.relopausable import TopLevelService

# ----------------
# Module constants
# ----------------

# Custom Windows service control in the range of [128-255]
SERVICE_CONTROL_RELOAD = 128

# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------


# ----------
# Main Class
# ----------

class TESSWindowsService(win32serviceutil.ServiceFramework):
	"""
	Windows service for the TESS database.
	"""
	_svc_name_         = "tessdb"
	_svc_display_name_ = "{0} Windows service {1}".format( IService(application).name , __version__)
	_svc_description_  = "TESS database service"


	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		

	def SvcStop(self):
		'''Service Stop entry point'''
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		reactor.callFromThread(reactor.stop)
		sysLogInfo("Stopping {0} {1} Windows service".format( IService(application).name, __version__ ))

	# -----------------------------------------------------------------
	#  SvcPause() &  SvcContinue() only applicable to pausable services
	# -----------------------------------------------------------------

	def SvcPause(self):
		'''Service Pause entry point'''
		self.ReportServiceStatus(win32service.SERVICE_PAUSE_PENDING)
		reactor.callFromThread(TopLevelService.sigpause)
		sysLogInfo("Pausing {0} {1} Windows service".format( IService(application).name, __version__ ))
		self.ReportServiceStatus(win32service.SERVICE_PAUSED)
		

	def SvcContinue(self):
		'''Service Continue entry point'''
		self.ReportServiceStatus(win32service.SERVICE_CONTINUE_PENDING)
		reactor.callFromThread(TopLevelService.sigresume)
		sysLogInfo("Resuming {0} {1} Windows service".format( IService(application).name, __version__ ))
		self.ReportServiceStatus(win32service.SERVICE_RUNNING)
		

	def SvcOtherEx(self, control, event_type, data):
		'''Implements a Reload functionality as a service custom control'''
		if control == SERVICE_CONTROL_RELOAD:
			self.SvcDoReload()
		else:
			self.SvcOther(control)


	def SvcDoReload(self):
		sysLogInfo("Reloading {0} {1} Windows service".format( IService(application).name, __version__ ))
		reactor.callFromThread(TopLevelService.sigreload)


	def SvcDoRun(self):
		'''Service Run entry point'''
		# initialize your services here
		sysLogInfo("Starting {0} {1}".format(IService(application).name, __version__))
		IService(application).startService()
		reactor.run(installSignalHandlers=0)
		sysLogInfo("{0} {1} Windows service stopped".format( IService(application).name, __version__ ))

     
def ctrlHandler(ctrlType):
    return True

if not servicemanager.RunningAsService():   
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
    win32serviceutil.HandleCommandLine(TESSWindowsService)
