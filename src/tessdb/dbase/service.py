# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------


import os
import sqlite3
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.application.service import Service
from twisted.logger import Logger
from twisted.enterprise import adbapi


from twisted.internet import reactor, task, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

# -------------------
# Third party imports
# -------------------

#--------------
# local imports
# -------------

from . import NAMESPACE
from .dbutils import create_or_open_database
from .tess import TESS
from .tess_readings import TESSReadings
from .tess_units import TESSUnits
from tessdb.logger import Logger, setLogLevel

# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------

def getPool(*args, **kargs):
    '''Get connetion pool for sqlite3 driver'''
    kargs['check_same_thread'] = False
    return adbapi.ConnectionPool("sqlite3", *args, **kargs)

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

    def __init__(self, path,  options, **kargs):
        super().__init__()   
        if options['type'] != "sqlite3":
            raise NotImplementedError(f"Database type not implemented: {options['type']}")
        self.path = path
        self.pool = None
        self.preferences = None
        self.getPoolFunc = getPool
        self.options  = options
        self.paused   = False
        self.onBoot   = True
        self.timeStatList  = []
        self.nrowsStatList = []
        # Create subordinate objects
        self.tess           = TESS()
        self.tess_units     = TESSUnits()
        self.tess_readings  = TESSReadings(self)
    
    #------------
    # Service API
    # ------------

    def startService(self):
        setLogLevel(namespace=NAMESPACE, levelStr='warn')
        if self.options['secs_resolution'] not in self.SECS_RESOLUTION:
            raise DiscreteValueError(self.options['secs_resolution'], self.SECS_RESOLUTION)
        connection, uuid = create_or_open_database(self.path)
        connection.commit()
        connection.close()
        super().startService()
        setLogLevel(namespace=NAMESPACE, levelStr=self.options['log_level'])
        setLogLevel(namespace='registry', levelStr=self.options['register_log_level'])
        log.info("Database operational. UUID = {uuid}", uuid=uuid)
        
        # setup the connection pool for asynchronouws adbapi
        self.openPool()
        self.startTasks()

    def stopService(self):
        self.closePool()
        d = Service.stopService()
        log.info("Database stopped.")
        return d


    def startTasks(self):
        '''Start periodic tasks'''
        self.later = reactor.callLater(2, self.writter)

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


    #---------------------
    # Extended Service API
    # --------------------

    def reloadService(self, new_options):
        '''
        Reload configuration.
        Returns a Deferred
        '''
        setLogLevel(namespace=NAMESPACE, levelStr=new_options['log_level'])
        setLogLevel(namespace='register', levelStr=new_options['register_log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        self.tess_readings.setOptions(auth_filter=new_options['auth_filter'])
        self.options = new_options
        # self.tess.invalidCache()
        # self.tess_locations.invalidCache()
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
        pool  = self.getPoolFunc(self.path)
        self.pool = pool
        self.tess.openPool(pool)
        self.tess_units.openPool(pool)
        self.tess_readings.openPool(pool)
        log.debug("Opened DB Connection Pool to {conn!s}", conn=self.path)


    def closePool(self):
        '''setup the connection pool for asynchronouws adbapi'''
        self.pool.close()
        self.tess.closePool()
        self.tess_units.closePool()
        self.tess_readings.closePool()
        log.debug("Closed DB Connection Pool to {conn!s}", conn=self.path)