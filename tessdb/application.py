# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys
from collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger, LogLevel
from twisted.internet import reactor, task
from twisted.internet.defer import inlineCallbacks

#--------------
# local imports
# -------------

from .config import VERSION_STRING, loadCfgFile
from .mqttservice import MQTTService
from .dbservice   import DBaseService
from .logger import setLogLevel

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='tessdb')



class TESSApplication(object):

    # Pointer to self
    instance = None

    # Signal handler polling period
    T = 1

    # Periodic task in seconds
    TLOG = 60

    def __init__(self, cfgFilePath, config_opts):
        
        TESSApplication.instance = self
        self.cfgFilePath = cfgFilePath
        self.queue  = { 'register':  deque() , 'readings':   deque() }
        self.sigreload  = False
        self.sigpause   = False
        self.sigresume  = False
        self.task       = task.LoopingCall(self.sighandler)
        self.task.start(self.T, now=False) # call every T seconds
        self.reportTask   = task.LoopingCall(self.reporter)
        self.mqttService  = MQTTService(self, config_opts['mqtt'])
        self.dbaseService = DBaseService(self, config_opts['dbase'])
        setLogLevel(namespace='tessdb', levelStr=config_opts['tessdb']['log_level'])
       

    def reporter(self):
        '''
        Periodic task to log queue size
        '''
        log.info("Readings queue size is {size}", size=len(self.queue['readings']))


    def sighandler(self):
        '''
        Periodic task to check for signal events
        '''
        if self.sigreload:
            self.sigreload = False
            self.reload()
        if self.sigpause:
            self.sigpause = False
            self.pause()
        if self.sigresume:
            self.sigresume = False
            self.resume()


    def pause(self):
        '''
        Pause application
        '''
        self.dbaseService.pauseService()
        if not self.reportTask.running:
            self.reportTask.start(self.TLOG, now=True) # call every T seconds


    def resume(self):
        '''
        Resume application
        '''
        self.dbaseService.resumeService()
        if self.reportTask.running:
            self.reportTask.stop()


    def reload(self):
        '''
        Reload application parameters
        '''
        config_opts  = loadCfgFile(self.cfgFilePath)
        self.mqttService.reloadService(config_opts['mqtt'])
        self.dbaseService.reloadService(config_opts['dbase'])
        level = config_opts['tessdb']['log_level']
        setLogLevel(namespace='tessdb', levelStr=level)
        log.info("new log level is {lvl}", lvl=level)
     

    def run(self, installSignalHandlers=1):
        log.info('running {tessdb}', tessdb=VERSION_STRING)
        self.dbaseService.startService()    # This is asynchronous !
        self.mqttService.startService()
        reactor.run(installSignalHandlers)