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
import platform

from   collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task
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
NAMESPACE = 'filt'

# -----------------------
# Module global variables
# -----------------------

log  = Logger(namespace=NAMESPACE)

class FilterService(Service):

    NAME = 'FilterService'


    def __init__(self, options, **kargs):
        Service.__init__(self)
        self.options    = options
        self.depth = options['depth']
        self.fifos = dict()
        setLogLevel(namespace=NAMESPACE, levelStr=options['log_level'])
        
    
    # -----------
    # Service API
    # -----------
    
    def startService(self):
        log.info("starting Filtering Service with depth = {depth}",depth=self.depth)
        reactor.callLater(0, self.filter)


    @inlineCallbacks
    def stopService(self):
        try:
            yield Service.stopService(self)
        except Exception as e:
            log.error("Exception {excp!s}", excp=e)
            reactor.stop()


    @inlineCallbacks
    def reloadService(self, new_options):
       
        setLogLevel(namespace=NAMESPACE, levelStr=new_options['log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        self.options = new_options
        

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
        Invalide frequencies have a value of zero
        '''
        return sum(aList) == 0

    @inlineCallbacks
    def filter(self):
        '''
        Task driven by deferred readings
        '''
        log.debug("starting Filtering infinite loop")
        while True:
            new_sample = yield self.parent.queue['tess_readings'].get()
            log.debug("Filter({log_tag}): got a new sample from {sample.name} with seq = {sample.seq}, freq = {sample.freq}", sample=new_sample, log_tag=new_sample['name'])
            fifo   = self.fifos.get(sample['name'], deque(self.depth))
            fifo.append(sample)
            if len(fifo == self.depth):
              seqList   = [ item['seq']  for item in fifo ]
              freqList  = [ item['freq'] for item in fifo ]
              old_sample = fifo.popleft()
              if self.isSequenceMonotonic(seqList) and self.isSequenceInvalid(freqList): 
                log.debug("Filter({log_tag}): discarding {sample.name} with seq = {sample.seq}, freq = {sample.freq}", sample=old_sample, log_tag=old_sample['name'])
              else:
                log.debug("Filter({log_tag}): giving {sample.name} with seq = {sample.seq} , freq = {sample.freq} to database queue", sample=old_sample, log_tag=old_sample['name'])
                self.parent.queue['tess_filtered_readings'].append(old_sample)
