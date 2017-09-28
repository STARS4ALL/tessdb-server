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
import tabulate

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
        self.sunriseTask  = task.LoopingCall(self.sunrise)
        setLogLevel(namespace='dbase', levelStr=options['log_level'])
        setLogLevel(namespace='register', levelStr=options['register_log_level'])
        if self.options['secs_resolution'] not in self.SECS_RESOLUTION:
            raise DiscreteValueError(self.options['secs_resolution'], self.SECS_RESOLUTION)
        
      
    #------------
    # Service API
    # ------------


    def startTasks(self):
        '''Start periodic tasks'''
        self.later = reactor.callLater(2, self.writter)
        self.sunriseTask.start(self.T_SUNRISE, now=True)

    @inlineCallbacks
    def schema(self):
        '''Create the schema and populate database'''

        # Import appropiate DAO module
        if self.options['type'] == "sqlite3":
            from .sqlite3 import getPool, Date, TimeOfDay, TESSUnits, Location, TESS, TESSReadings
        else:
            msg = "No database driver found for '{0}'".format(self.options['type'])
            raise ImportError( msg )
        # Create DAO objects
        self.pool           = getPool(self.options['connection_string'])
        self.tess           = TESS(self.pool)
        self.tess_units     = TESSUnits(self.pool)
        self.tess_readings  = TESSReadings(self.pool, self)
        self.tess_locations = Location(self.pool)
        self.date           = Date(self.pool)
        self.time           = TimeOfDay(self.pool, self.options['secs_resolution'])

        # Create and Populate Database
        self.tess_readings.setOptions(location_filter=self.options['location_filter'], location_horizon=self.options['location_horizon'])
        yield self.date.schema(date_fmt=self.options['date_fmt'], year_start=self.options['year_start'], year_end=self.options['year_end'])
        yield self.time.schema(json_dir=self.options['json_dir'])
        yield self.tess_locations.schema(json_dir=self.options['json_dir'])
        yield self.tess.schema(json_dir=self.options['json_dir'])
        yield self.tess_units.schema(json_dir=self.options['json_dir'])
        yield self.tess_readings.schema(json_dir=self.options['json_dir'])

    @inlineCallbacks
    def startService(self):
        log.info("starting DBase Service on {database}", database=self.options['connection_string'])
        yield self.schema()
        self.startTasks()
        # Remainder Service initialization
        Service.startService(self)
        log.info("Database operational.")
      
    def stopService(self):
        self.pool.close()
        d = Service.stopService()
        log.info("Database stopped.")
        return d

    #---------------------
    # Extended Service API
    # --------------------

    @inlineCallbacks
    def reloadService(self, new_options):
        '''
        Reload configuration.
        Returns a Deferred
        '''
        setLogLevel(namespace='dbase', levelStr=new_options['log_level'])
        setLogLevel(namespace='register', levelStr=new_options['register_log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        
        self.tess_readings.setOptions(location_filter=new_options['location_filter'], 
            location_horizon=new_options['location_horizon'])
        yield self.date.populate(json_dir=new_options['json_dir'])
        yield self.time.populate(json_dir=new_options['json_dir'])
        yield self.tess_locations.populate(json_dir=new_options['json_dir'])
        yield self.tess_units.populate(json_dir=new_options['json_dir'])
        yield self.tess.populate(json_dir=new_options['json_dir'])

        
    def pauseService(self):
        log.info('TESS database writer paused')
        self.paused = True
        return defer.succeed(None)

    def resumeService(self):
        log.info('TESS database writer resumed')
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
        if self.options['stats'] == "":
            return
        
        # get readings stats
        resultRds = self.tess_readings.getCounters()
        global_nok = resultRds[1:]
        global_nok_sum = sum(resultRds[1:])
        global_ok_sum  = resultRds[0] - global_nok_sum
        global_stats   = (resultRds[0], global_ok_sum, global_nok_sum)
        global_stats_nok  = (global_nok_sum, resultRds[1], resultRds[2], resultRds[3], resultRds[4], resultRds[5])
        
        # get registration stats
        resultReg = self.tess.getCounters()
        global_ok_sum_reg  = sum(resultReg[1:4])
        global_nok_sum_reg = sum(resultReg[4:])
        global_stats_reg   = (resultReg[0], global_ok_sum_reg, global_nok_sum_reg)
        ok_stats_reg       = (global_ok_sum_reg, resultReg[1], resultReg[2], resultReg[3])
        nok_stats_reg      = (global_nok_sum_reg, resultReg[4], resultReg[5])

        # Efficiency stats
        resultEff = yield deferToThread(self.getCounters)

        # Readings statistics
        if self.options['stats'] == "detailed":
            log.info("DB Readings Statistics during the last hour")
            text = tabulate.tabulate([global_stats], headers=['DB Readings Total','OK','NOK'], tablefmt='grid')
            log.info("\n{table}",table=text)   
            
            text = tabulate.tabulate([global_stats_nok], headers=['DB Readings Total NOK','Not Registered','Lack Sunrise','Daytime','Dupl','Other'], tablefmt='grid')
            log.info("\n{table}",table=text)
           
            # Registration statistics
            log.info("DB Registrations Statistics during the last hour")
            text = tabulate.tabulate([global_stats_reg], headers=['DB Registration Total','OK','NOK'], tablefmt='grid')
            log.info("\n{table}",table=text)

            text = tabulate.tabulate([ok_stats_reg], headers=['DB Registration Total OK','Created','Upd Name','Upd Calib'], tablefmt='grid')
            log.info("\n{table}",table=text)

            text = tabulate.tabulate([nok_stats_reg], headers=['DB Registration NOK','No Upd Name','No Create Name'], tablefmt='grid')
            log.info("\n{table}",table=text)
           
            # I/O efficiency stats
            log.info("DB I/O EFFICIENCY = {efficiency}%",efficiency=resultEff[1])
            text = tabulate.tabulate(resultEff[0], headers=['Stat. (N = {0})'.format(resultEff[2]),'Min','Aver','Max'], tablefmt='grid')
            log.info("\n{table}",table=text)

        elif self.options['stats'] == "condensed":

            log.info("DB Stats Readings [Total, OK, NOK] = {global_stats_rds!s}", global_stats_rds=global_stats)
            log.info("DB Stats Register [Total, OK, NOK] = {global_stats_reg!s}", global_stats_reg=global_stats_reg)
            log.info("DB Stats I/O Effic. [Nsec, %, Tmin, Taver, Tmax, Naver] = [{Nsec}, {eff:0.2g}%, {Tmin:0.2g}, {Taver:0.2g}, {Tmax:0.2g}, {Naver:0.2g}]",
                Nsec=resultEff[2], 
                eff=resultEff[1], 
                Tmin=resultEff[0][0][1], 
                Taver=resultEff[0][0][2],
                Tmax=resultEff[0][0][3],
                Naver=resultEff[0][1][2]
            )
        else:
            pass



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
        l0 = len(self.parent.queue['tess_readings']) + len(self.parent.queue['tess_register'])
        if not self.paused:
            while len(self.parent.queue['tess_register']):
                row = self.parent.queue['tess_register'].popleft()
                yield self.register(row)
            while len(self.parent.queue['tess_readings']):
                row = self.parent.queue['tess_readings'].popleft()
                yield self.update(row)
        self.timeStatList.append( (datetime.datetime.utcnow() - t0).total_seconds())
        self.nrowsStatList.append(l0)
        self.later = reactor.callLater(self.T_QUEUE_POLL,self.writter)
        

    # ---------------------
    # sunrise periodic Task
    # ---------------------

    @inlineCallbacks
    def sunrise(self, today=utcstart()):
        if self.paused or not self.options['location_filter']:
            returnValue(None)

        # Unitary testing passes an specific value of 'today'
        # Normal operation leaves this to a default value 'utcstart()'
        if today == utcstart():
            today = utcnoon()

        log.info("Sunrise Task: ON BOOT = {onboot} today = {today!s}", onboot=self.onBoot, today=today)
        # Only compute Sunrise/Sunset once a day around midnight
        # with sampling resolution given by T_SUNRISE
        if  not self.onBoot and utcnow() - utcmidnight() > self.T_SUNRISE * ephem.second:
              returnValue(None)
        self.onBoot    = False  
        batch_perc     = self.options['location_batch_size']
        batch_min_size = self.options['location_minimum_batch_size']
        horizon        = self.options['location_horizon']
        pause          = self.options['location_pause']
        yield self.tess_locations.sunrise(batch_perc=batch_perc, 
            batch_min_size=batch_min_size, horizon=horizon, pause=pause, today=today)
      
   

