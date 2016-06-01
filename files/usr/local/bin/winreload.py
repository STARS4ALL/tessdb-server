## ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# -----------------
# Win32 API Modules
# -----------------

import win32event
import win32api
import win32con
import win32evtlogutil

import win32serviceutil
import servicemanager  
import win32service

# Custom Windows service control in the range of [128-255]
SERVICE_CONTROL_RELOAD = 128
SERVICE_NAME = "tessdb"

# Get access to the Service Control Manager
hscm = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)

# Open the desired service with
hs = win32serviceutil.SmartOpenService(hscm, SERVICE_NAME, win32service.SERVICE_ALL_ACCESS)

# Send the custom control
win32service.ControlService(hs, SERVICE_CONTROL_RELOAD)

# Close the service (probably not necessary)
win32service.CloseServiceHandle(hs)



    