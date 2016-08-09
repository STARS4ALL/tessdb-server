# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import sys
from   collections import deque

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

from tessdb.service.relopausable import MultiService

from tessdb.config      import VERSION_STRING, loadCfgFile
from tessdb.mqttservice import MQTTService
from tessdb.dbservice   import DBaseService
from tessdb.logger      import setLogLevel

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='tessdb')



class TESSDBService(MultiService):

    # Service name
    NAME = 'TESSDB'

    # Stats period task in seconds
    T_STAT = 3600

    def __init__(self, config_opts, cfgFilePath):
        MultiService.__init__(self)
        self.cfgFilePath = cfgFilePath
        self.queue  = { 'tess_register':  deque() , 'tess_readings':   deque() }
        self.statsTask    = task.LoopingCall(self.logCounters)
        setLogLevel(namespace='tessdb', levelStr=config_opts['log_level'])

    # -----------
    # Service API
    # -----------

    @inlineCallbacks
    def startService(self):
        log.info('starting {tessdb}', tessdb=VERSION_STRING)
        self.dbaseService   = self.getServiceNamed(DBaseService.NAME)
        self.mqttService    = self.getServiceNamed(MQTTService.NAME)
        yield self.dbaseService.startService()    # This is asynchronous !
        self.mqttService.startService()
        self.statsTask.start(self.T_STAT, now=False) # call every T seconds


    def pauseService(self):
        '''
        Pause services
        '''
        return self.dbaseService.pauseService()


    def resumeService(self):
        '''
        Resume services
        '''
        return self.dbaseService.resumeService()


    @inlineCallbacks
    def reloadService(self, options):
        '''
        Reload service parameters
        '''
        log.warn("{tessdb} config being reloaded", tessdb=VERSION_STRING)
        try:
            config_opts  = yield deferToThread(loadCfgFile, self.cfgFilePath)
        except Exception as e:
            log.error("Error trying to reload: {excp!s}", excp=e)
        else:
            yield self.mqttService.reloadService(config_opts['mqtt'])
            yield self.dbaseService.reloadService(config_opts['dbase'])
            level = config_opts['tessdb']['log_level']
            setLogLevel(namespace='tessdb', levelStr=level)
            log.info("new log level is {lvl}", lvl=level)
            # It is very convenient to recompute all sunrise/sunset data after a reload
            # After having assigned an instrument to a location
            # Otherwise, I have to restart tssdb and loose some samples
            yield self.dbaseService.sunrise() # This is asynchronous !
    
    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.mqttService.resetCounters()
        self.dbaseService.resetCounters()

    @inlineCallbacks
    def logCounters(self):
        '''log stat counters'''
        self.mqttService.logCounters()
        yield self.dbaseService.logCounters()
        self.resetCounters()
