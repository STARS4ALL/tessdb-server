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
import signal
import errno
import sys
import datetime
import json
import math
import platform

from   collections import deque

# No xrange in Python3
try:
    xrange
except NameError:
    xrange = range

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task, defer
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet.endpoints import clientFromString
from twisted.internet.defer import inlineCallbacks


#--------------
# local imports
# -------------
from tessdb.service.relopausable import Service

from tessdb.logger import setLogLevel

# ----------------
# Module constants
# ----------------

# Service Logging namespace
NAMESPACE = 'filtr'

# -----------------------
# Module global variables
# -----------------------

log  = Logger(namespace=NAMESPACE)



class FilterService(Service):

    NAME = 'FilterService'

    sigflushing = False

    @staticmethod
    def sigflush(signum, frame):
        '''
        Signal handler (SIGWINCH)
        '''
        FilterService.sigflushing = True


    def __init__(self, options, **kargs):
        Service.__init__(self)
        self.options  = options
        self.depth    = options['depth']
        self.enabled  = options['enabled']
        self.fifos    = dict()
        setLogLevel(namespace=NAMESPACE, levelStr=options['log_level'])
        
    
    # -----------
    # Service API
    # -----------
    
    def startService(self):
        log.info("starting Filtering Service with depth = {depth}",depth=self.depth)
        if not self.enabled:
            log.warn("actual filtering is disabled, passing all samples to the database qeeue")
        reactor.callLater(0, self.filter)


    @inlineCallbacks
    def stopService(self):
        try:
            yield Service.stopService(self)
        except Exception as e:
            log.error("Exception {excp!s}", excp=e)
            reactor.stop()


    def reloadService(self, new_options):
        setLogLevel(namespace=NAMESPACE, levelStr=new_options['log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        log.info("new filtering status is {flag}", flag=new_options['enabled'])
        if self.enabled == True and new_options['enabled'] == False:
            self.flush()
        self.options  = new_options
        self.enabled  = self.options['enabled']
        return defer.succeed(None)
        

    # --------------
    # Helper methods
    # ---------------

    def isSequenceMonotonic(self, aList):
        # Calculate first difference
        first_diff = [aList[i+1] - aList[i] for i in xrange(len(aList)-1)]
        # Modified second difference with absolute values, to avoid cancellation 
        # in final sum due to symmetric differences
        second_diff = [abs(first_diff[i+1] - first_diff[i])   for i in xrange(len(first_diff)-1)]
        return sum(second_diff) == 0


    def isSequenceInvalid(self, aList):
        '''
        Invalid magnitudes have a value of zero
        '''
        return sum(aList) == 0


    def flush(self):
        '''
        Flushes FIFOs into output queue
        '''
        for name in self.fifos:
            log.debug("flushing {log_tag} fifo", log_tag=name)
            while len(self.fifos[name]) > self.depth//2:
                self.fifos[name].popleft()
            while len(self.fifos[name]) != 0:
                self.parent.queue['tess_filtered_readings'].append(self.fifos[name].popleft())
        self.fifos = dict()


    def doFilter(self, new_sample):
        fifo   = self.fifos.get(new_sample['name'], deque(maxlen=self.depth))
        self.fifos[new_sample['name']] = fifo  # Create new fifo if not already
        fifo.append(new_sample)
        if len(fifo) <= self.depth//2:
            log.debug("{log_tag}: Refilling the fifo", log_tag=new_sample['name'])
            return
        chosen_sample = fifo[self.depth//2]
        seqList  = [ item['seq'] for item in fifo ]
        magList  = [ item['mag'] for item in fifo ]
        log.debug("{log_tag}: seqList = {s}. magList = {m}", s=seqList, m=magList, log_tag=new_sample['name'])
        if self.isSequenceMonotonic(seqList) and self.isSequenceInvalid(magList): 
            log.debug("discarding {log_tag} sample with seq = {seq}, mag ={mag}, freq = {freq}",  
                mag=chosen_sample['mag'], 
                seq=chosen_sample['seq'], 
                freq=chosen_sample['freq'], 
                log_tag=chosen_sample['name'])
        else:
            log.debug("accepting {log_tag} sample with seq = {seq}, mag ={mag}, freq = {freq}",  
                seq=chosen_sample['seq'], 
                mag=chosen_sample['mag'], 
                freq=chosen_sample['freq'], 
                log_tag=chosen_sample['name'])
            self.parent.queue['tess_filtered_readings'].append(chosen_sample)


              
    # --------------
    # Main task
    # ---------------

    @inlineCallbacks
    def filter(self):
        '''
        Task driven by deferred readings
        '''
        log.debug("starting Filtering infinite loop")
        while True:
            if FilterService.sigflushing:
                FilterService.sigflushing = False
                log.warn("flushing filtering queues")
                self.flush()    # Flush filters
            new_sample = yield self.parent.queue['tess_readings'].get()
            log.debug("got a new sample from {log_tag}", log_tag=new_sample['name'])
            if self.enabled:
                self.doFilter(new_sample)
            else:
                self.parent.queue['tess_filtered_readings'].append(new_sample)
        
        

# Install a custom signal handler
signal.signal(signal.SIGWINCH, FilterService.sigflush)