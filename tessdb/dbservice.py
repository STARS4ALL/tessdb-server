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
import errno
import sys
import datetime
import json
import math

import ephem

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task, defer
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

#--------------
# local imports
# -------------

from tessdb.service.relopausable import Service
from tessdb.logger import setLogLevel
from tessdb.error  import DiscreteValueError

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


def utcstart():
    '''Returns the ephem Date object at the beginning of our valid time'''
    return ephem.Date("0001/1/1 00:00:00")

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

    # Service name
    NAME = 'DBaseService'

    # Sunrise/Sunset Task period in seconds
    T_SUNRISE = 3600
    T_QUEUE_POLL = 1
    SECS_RESOLUTION = [60, 30, 20, 15, 12, 10, 6, 5, 4, 3, 2, 1]

    def __init__(self, options, **kargs):
        Service.__init__(self)
        self.options  = options
        self.paused   = False
        self.onBoot   = True
        self.timeStatList  = []
        self.nrowsStatList = []
        
        setLogLevel(namespace='dbase', levelStr=options['log_level'])
        setLogLevel(namespace='registry', levelStr=options['register_log_level'])
        if self.options['secs_resolution'] not in self.SECS_RESOLUTION:
            raise DiscreteValueError(self.options['secs_resolution'], self.SECS_RESOLUTION)
        
        # Import appropiate DAO module
        if self.options['type'] == "sqlite3":
            import sqlite3
            from .sqlite3 import getPool, Date, TimeOfDay, TESSUnits, Location, TESS, TESSReadings
            if not os.path.exists(options['connection_string']):
                 raise IOError("No SQLite3 Database file found in {0}. Exiting ...".format(options['connection_string']))
            # synchronous database initialization uses standard API, not adbapi
            connection = sqlite3.connect(options['connection_string'])
            self.getPoolFunc = getPool
        else:
            msg = "No database driver found for '{0}'".format(self.options['type'])
            raise ImportError( msg )

        # Create DAO objects
        self.pool           = None
        self.connection     = connection
        self.tess           = TESS(connection)
        self.tess_units     = TESSUnits(connection)
        self.tess_readings  = TESSReadings(connection, self)
        self.tess_locations = Location(connection)
        self.date           = Date(connection)
        self.time           = TimeOfDay(connection, self.options['secs_resolution'])
      
    #------------
    # Service API
    # ------------


    def startTasks(self):
        '''Start periodic tasks'''
        self.later = reactor.callLater(2, self.writter)

    def schema(self):
        '''Create the schema and populate database'''
        self.tess_readings.setOptions(auth_filter=self.options['auth_filter'])
        self.date.schema(date_fmt=self.options['date_fmt'], year_start=self.options['year_start'], year_end=self.options['year_end'])
        self.time.schema()
        self.tess_locations.schema()
        self.tess.schema()
        self.tess_units.schema()
        self.tess_readings.schema()
        self.tess.connection           = None
        self.tess_units.connection     = None
        self.tess_readings.connection  = None
        self.tess_locations.connection = None
        self.date.connection           = None
        self.time.connection           = None
        self.connection.close()


    def startService(self):
        log.info("starting DBase Service on {database}", database=self.options['connection_string'])
        self.schema()
        # setup the connection pool for asynchronouws adbapi
        self.openPool()
        self.startTasks()
        # Remainder Service initialization
        Service.startService(self)
        log.info("Database operational.")
      
    def stopService(self):
        self.closePool()
        d = Service.stopService()
        log.info("Database stopped.")
        return d

    #---------------------
    # Extended Service API
    # --------------------

    def reloadService(self, new_options):
        '''
        Reload configuration.
        Returns a Deferred
        '''
        setLogLevel(namespace='dbase', levelStr=new_options['log_level'])
        setLogLevel(namespace='register', levelStr=new_options['register_log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        self.tess_readings.setOptions(auth_filter=new_options['auth_filter'])
        self.options = new_options
        self.tess.invalidCache()
        self.tess_locations.invalidCache()
        return defer.succeed(None)
        

        
    def pauseService(self):
        log.info('TESS database writer paused')
        if not self.paused:
            self.paused = True
            if self.options["close_when_pause"]:
                self.closePool()
        return defer.succeed(None)


    def resumeService(self):
        log.info('TESS database writer resumed')
        if self.paused:
            if self.options["close_when_pause"]:
                self.openPool()
            self.paused = False
        return defer.succeed(None)

    # ---------------
    # OPERATIONAL API
    # ---------------

    def register(self, row):
        '''
        Registers an instrument given its MAC address, friendly name and calibration constant.
        Returns a Deferred
        '''
        return self.tess.register(row)

    def update(self, row):
        '''
        Update readings table
        Returns a Deferred 
        '''
        return self.tess_readings.update(row)

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.tess_readings.resetCounters()
        self.tess.resetCounters()
        self.timeStatList  = []
        self.nrowsStatList = []

    def getCounters(self):
        N = len(self.nrowsStatList)
        if not N:
            timeStats = ["UNDEF I/O Time (sec.)", 0, 0, 0]
            rowsStats = ["UNDEF Pend Samples", 0, 0, 0]
            efficiency = 0
        else:
            timeStats = [ "I/O Time (sec.)", min(self.timeStatList),  sum(self.timeStatList)/N,  max(self.timeStatList) ]
            rowsStats = [ "Pend Samples", min(self.nrowsStatList), sum(self.nrowsStatList)/N, max(self.nrowsStatList) ]
            efficiency = (100 * N * self.T_QUEUE_POLL) / float(self.parent.T_STAT)
        return ((timeStats, rowsStats), efficiency, N)

    @inlineCallbacks
    def logCounters(self):
        '''log stat counters'''
        
        # get readings stats
        resultRds = self.tess_readings.getCounters()
        global_nok = resultRds[1:]
        global_nok_sum = sum(resultRds[1:])
        global_ok_sum  = resultRds[0] - global_nok_sum
        global_stats   = (resultRds[0], global_ok_sum, global_nok_sum)
        global_stats_nok  = (global_nok_sum, resultRds[1], resultRds[2], resultRds[3], resultRds[4], resultRds[5])
        
        # get registration stats
        labelReg, resultReg = self.tess.getCounters()

        # Efficiency stats
        resultEff = yield deferToThread(self.getCounters)

        # Readings statistics
        log.info("DB Stats Readings [Total, OK, NOK] = {global_stats_rds!s}", global_stats_rds=global_stats)
        log.info("DB Stats Register {labelReg!s} = {resultReg!s}", labelReg=labelReg, resultReg=resultReg)
        log.info("DB Stats NOK details [Not Reg, Not Auth, Daylight, Dup, Other] = [{Reg}, {Auth}, {Sun}, {Dup}, {Other}]", 
            Reg=resultRds[1], Auth=resultRds[2], Sun=resultRds[3], Dup=resultRds[4], Other=resultRds[5])
        log.info("DB Stats I/O Effic. [Nsec, %, Tmin, Taver, Tmax, Naver] = [{Nsec}, {eff:0.2g}%, {Tmin:0.2g}, {Taver:0.2g}, {Tmax:0.2g}, {Naver:0.2g}]",
            Nsec=resultEff[2], 
            eff=resultEff[1], 
            Tmin=resultEff[0][0][1], 
            Taver=resultEff[0][0][2],
            Tmax=resultEff[0][0][3],
            Naver=resultEff[0][1][2]
        )

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
        t0 = datetime.datetime.utcnow()
        l0 = len(self.parent.queue['tess_filtered_readings']) + len(self.parent.queue['tess_register'])
        if not self.paused:
            while len(self.parent.queue['tess_register']):
                row = self.parent.queue['tess_register'].popleft()
                yield self.register(row)
            while len(self.parent.queue['tess_filtered_readings']):
                row = self.parent.queue['tess_filtered_readings'].popleft()
                yield self.update(row)
        self.timeStatList.append( (datetime.datetime.utcnow() - t0).total_seconds())
        self.nrowsStatList.append(l0)
        self.later = reactor.callLater(self.T_QUEUE_POLL,self.writter)
        

      
    # ==============
    # Helper methods
    # ==============

    def openPool(self):
        # setup the connection pool for asynchronouws adbapi
        log.info("Opening a DB Connection to {conn!s}", conn=self.options['connection_string'])
        self.pool  = self.getPoolFunc(self.options['connection_string'])
        self.tess.pool           = self.pool
        self.tess_units.pool     = self.pool
        self.tess_readings.pool  = self.pool
        self.tess_locations.pool = self.pool
        self.date.pool           = self.pool
        self.time.pool           = self.pool
        log.info("Opened a DB Connection to {conn!s}", conn=self.options['connection_string'])


    def closePool(self):
        '''setup the connection pool for asynchronouws adbapi'''
        log.info("Closing a DB Connection to {conn!s}", conn=self.options['connection_string'])
        self.pool.close()
        log.info("Closed a DB Connection to {conn!s}", conn=self.options['connection_string'])
