# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import errno
import sys
import datetime
import json
import ephem
# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task
from twisted.application.service import Service
from twisted.internet.defer import inlineCallbacks, returnValue

#--------------
# local imports
# -------------

from .logger import setLogLevel

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='dbase')

# ------------------------
# Module Utility Functions
# ------------------------

def utcnoon():
    '''Returns the ephem Date object at today's noon'''
    return ephem.Date(datetime.datetime.utcnow().replace(hour=12, minute=0, second=0,microsecond=0))

def utcmidnight():
    '''Returns the ephem Date object at today's midnight'''
    return ephem.Date(datetime.datetime.utcnow().replace(hour=0, minute=0, second=0,microsecond=0))

def utcnow():
    '''Returns now's ephem Date object '''
    return ephem.Date(datetime.datetime.utcnow())
 
# --------------
# Module Classes
# --------------

class DBaseService(Service):

    # Sunrise/Sunset Task period in seconds
    T_SUNRISE = 3600

    def __init__(self, parent, options, **kargs):
        Service.__init__(self)
        self.parent   = parent
        self.options  = options
        self.paused   = False
        self.onBoot   = True
        self.sunriseTask  = task.LoopingCall(self.sunrise)
        setLogLevel(namespace='dbase', levelStr=options['log_level'])
      
    #------------
    # Service API
    # ------------

    @inlineCallbacks
    def startService(self):
        if self.options['type'] == "sqlite3":
            from .sqlite3 import DBase
        else:
            msg = "No database driver found for '{0}'".format(self.options['type'])
            raise ImportError( msg )
        log.info("starting DBase Service")
        self.dbase    = DBase(self.options['connection_string'])
        yield self.dbase.schema(
            json_dir=self.options['json_dir'], 
            date_fmt=self.options['date_fmt'], 
            year_start=self.options['year_start'], 
            year_end=self.options['year_end'], 
            replace=True)
        Service.startService(self)
        log.info("Database operational.")
        self.later = reactor.callLater(2, self.writter)
        self.sunriseTask.start(self.T_SUNRISE, now=True)

    def stopService(self):
        self.dbase.pool.close()
        Service.stopService()
        log.info("Database stopped.")

    #---------------------
    # Extended Service API
    # --------------------

    def reloadService(self, new_options):
        setLogLevel(namespace='dbase', levelStr=new_options['log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])

    def pauseService(self):
        log.info('TESS database writer paused')
        self.paused = True

    def resumeService(self):
        log.info('TESS database writer resumed')
        self.paused = False

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.dbase.resetCounters()


    def logCounters(self):
        '''log stat counters'''
        self.dbase.logCounters()

    # =============
    # Twisted Tasks
    # =============
   
    # ---------------------
    # Database writter task
    # ---------------------

    @inlineCallbacks
    def writter(self):
        '''
        Periodic task that takes rows from the queues
        and update them to database
        '''
        if not self.paused:
            while len(self.parent.queue['tess_register']):
                row = self.parent.queue['tess_register'].popleft()
                yield self.dbase.register(row)
            while len(self.parent.queue['tess_readings']):
                row = self.parent.queue['tess_readings'].popleft()
                yield self.dbase.update(row, self.options['location_filter'])
        self.later = reactor.callLater(1,self.writter)
        

    # ---------------------
    # sunrise periodic Task
    # ---------------------

    @inlineCallbacks
    def sunrise(self):
        if self.paused or not self.options['location_filter']:
            returnValue(None)

        log.info("ON BOOT = {onboot}", onboot=self.onBoot)
        # Only compute Sunrise/Sunset once a day around midnight
        # with sampling resolution given by T_SUNRISE
        if  not self.onBoot and utcnow() - utcmidnight() > self.T_SUNRISE * ephem.second:
              returnValue(None)
        self.onBoot    = False  
        batch_perc     = self.options['location_batch_size']
        batch_min_size = self.options['location_minimun_batch_size']
        horizon        = self.options['location_horizon']
        pause          = self.options['location_pause']
        yield self.dbase.tess_locations.sunrise(batch_perc=batch_perc, 
            batch_min_size=batch_min_size, horizon=horizon, pause=pause)
      
   

