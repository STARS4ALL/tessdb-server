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
from twisted.internet import task
from twisted.internet.defer  import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
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

    # Stats period task in seconds
    T_STAT = 3600

    def __init__(self, cfgFilePath, config_opts):
        
        TESSApplication.instance = self
        self.cfgFilePath = cfgFilePath
        self.queue  = { 'tess_register':  deque() , 'tess_readings':   deque() }
        self.sigreload  = False
        self.sigpause   = False
        self.sigresume  = False
        self.reloadTask   = task.LoopingCall(self.sighandler)
        self.reportTask   = task.LoopingCall(self.reporter)
        self.statsTask    = task.LoopingCall(self.logCounters)
        self.mqttService  = MQTTService(self, config_opts['mqtt'])
        self.dbaseService = DBaseService(self, config_opts['dbase'])
        setLogLevel(namespace='tessdb', levelStr=config_opts['tessdb']['log_level'])
        self.reloadTask.start(self.T, now=False) # call every T seconds

    def reporter(self):
        '''
        Periodic task to log queue size
        '''
        log.info("Readings queue size is {size}", size=len(self.queue['tess_readings']))


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

    @inlineCallbacks
    def reload(self):
        '''
        Reload application parameters
        '''
        try:
            config_opts  = yield deferToThread(loadCfgFile, self.cfgFilePath)
        except Exception as e:
            log.error("Error trying to reload: {excp!s}", excp=e)
        else:
            self.mqttService.reloadService(config_opts['mqtt'])
            self.dbaseService.reloadService(config_opts['dbase'])
            level = config_opts['tessdb']['log_level']
            setLogLevel(namespace='tessdb', levelStr=level)
            log.info("new log level is {lvl}", lvl=level)
    
    @inlineCallbacks
    def start(self):
        log.info('starting {tessdb}', tessdb=VERSION_STRING)
        yield self.dbaseService.startService()    # This is asynchronous !
        self.mqttService.startService()
        self.statsTask.start(self.T_STAT, now=False) # call every T seconds
    
    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.mqttService.resetCounters()
        self.dbaseService.resetCounters()

    def logCounters(self):
        '''log stat counters'''
        self.mqttService.logCounters()
        self.dbaseService.logCounters()
        self.resetCounters()

    