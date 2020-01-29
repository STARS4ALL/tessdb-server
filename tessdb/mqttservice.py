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

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet.endpoints import clientFromString
from twisted.internet.defer import inlineCallbacks

from mqtt import v311
from mqtt.error  import MQTTStateError
from mqtt.client.factory import MQTTFactory

#--------------
# local imports
# -------------
from tessdb.service.relopausable import Service

from tessdb.error import ValidationError, ReadingKeyError, ReadingTypeError, IncorrectTimestampError
from tessdb.logger import setLogLevel
from tessdb.utils  import chop

# ----------------
# Module constants
# ----------------

HOSTNAME = platform.uname()[1]

# Reconencting Service. Default backoff policy parameters

INITIAL_DELAY = 4   # seconds
FACTOR        = 2
MAX_DELAY     = 600 # seconds

# Sequence of possible timestamp formats comming from the Publishers
TSTAMP_FORMAT = [ "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",]

# Max Timestamp Ouf-Of-Sync difference, in seconds
MAX_TSTAMP_OOS = 60

# Service Logging namespace
NAMESPACE = 'mqttS'

# MQTT Protocol logging namespace
PROTOCOL_NAMESPACE = 'mqtt'

# -----------------------
# Module global variables
# -----------------------

# Dirty fix for Python3 not having an specific unicode type

if sys.version_info[0] > 2:
    class unicode: 
        pass



log  = Logger(namespace=NAMESPACE)

class MQTTService(ClientService):

    NAME = 'MQTTService'

    # Default subscription QoS
    
    QoS = 2
    
    # Mandatory keys in each register
    MANDATORY_REGR = set(['name','mac','calib','rev'])
    
    # Mandatory keys in each reading
    MANDATORY_READ = set(['seq','name','freq','mag','tamb','tsky','rev'])

    def __init__(self, options, **kargs):

        self.options    = options
        self.topics     = []
        self.regAllowed = False
        self.validate   = options['validation']
        setLogLevel(namespace=NAMESPACE, levelStr=options['log_level'])
        setLogLevel(namespace=PROTOCOL_NAMESPACE, levelStr=options['protocol_log_level'])

        self.tess_heads  = [ t.split('/')[0] for t in self.options['tess_topics'] ]
        self.tess_tails  = [ t.split('/')[2] for t in self.options['tess_topics'] ]
        self.factory     = MQTTFactory(profile=MQTTFactory.SUBSCRIBER)
        self.endpoint    = clientFromString(reactor, self.options['broker'])
        if self.options['username'] == "":
            self.options['username'] = None
            self.options['password'] = None
        self.resetCounters()
        ClientService.__init__(self, self.endpoint, self.factory, 
            retryPolicy=backoffPolicy(initialDelay=INITIAL_DELAY, factor=FACTOR, maxDelay=MAX_DELAY))
    
    # -----------
    # Service API
    # -----------
    
    def startService(self):
        log.info("starting MQTT Client Service")
        # invoke whenConnected() inherited method
        self.whenConnected().addCallback(self.connectToBroker)
        ClientService.startService(self)


    @inlineCallbacks
    def stopService(self):
        try:
            yield ClientService.stopService(self)
        except Exception as e:
            log.error("Exception {excp!s}", excp=e)
            reactor.stop()


    @inlineCallbacks
    def reloadService(self, new_options):
        self.validate  = new_options['validation']
        setLogLevel(namespace=NAMESPACE, levelStr=new_options['log_level'])
        setLogLevel(namespace=PROTOCOL_NAMESPACE, levelStr=new_options['protocol_log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        yield self.subscribe(new_options)
        self.options = new_options
        self.tess_heads  = [ t.split('/')[0] for t in self.options['tess_topics'] ]
        self.tess_tails  = [ t.split('/')[2] for t in self.options['tess_topics'] ]

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.npublish  = 0
        self.nreadings = 0
        self.nregister = 0
        self.nfilter   = 0

    def getCounters(self):
        return [ self.npublish, self.nreadings, self.nregister, self.nfilter ]

    def logCounters(self):
        '''log stat counters'''
        # get stats
        result = self.getCounters()
        log.info("MQTT Stats [Total, Reads, Register, Discard] = {counters!s}", counters=result)
        

    # --------------
    # Helper methods
    # ---------------
   
    @inlineCallbacks
    def connectToBroker(self, protocol):
        '''
        Connect to MQTT broker
        '''
        self.protocol                 = protocol
        self.protocol.onPublish       = self.onPublish
        self.protocol.onDisconnection = self.onDisconnection

        try:
            yield self.protocol.connect("TwistedMQTT-subs" + '@' + HOSTNAME, 
                username=self.options['username'], password=self.options['password'], 
                keepalive=self.options['keepalive'])
            yield self.subscribe(self.options)
        except Exception as e:
            log.error("Connecting to {broker} raised {excp!s}", 
               broker=self.options['broker'], excp=e)
        else:
            log.info("Connected and subscribed to {broker}", broker=self.options['broker'])
       

    @inlineCallbacks
    def subscribe(self, options):
        '''
        Smart subscription to a list of (topic, qos) tuples
        '''
        # Make the list of tuples first
        topics = [ (topic, self.QoS) for topic in options['tess_topics'] ]
        if options['tess_topic_register'] != "":
            self.regAllowed = True
            topics.append( (options['tess_topic_register'], self.QoS) )
        else:
            self.regAllowed = False
        # Unsubscribe first if necessary from old topics
        diff_topics = [ t[0] for t in (set(self.topics) - set(topics)) ]
        if len(diff_topics):
            log.info("Unsubscribing from topics={topics!r}", topics=diff_topics)
            res = yield self.protocol.unsubscribe(diff_topics)
            log.debug("Unsubscription result={result!r}", result=res)
        else:
            log.info("no need to unsubscribe")
        # Now subscribe to new topics
        diff_topics = [ t for t in (set(topics) - set(self.topics)) ]
        if len(diff_topics):
            log.info("Subscribing to topics={topics!r}", topics=diff_topics)
            res = yield self.protocol.subscribe(diff_topics)
            log.debug("Subscription result={result!r}", result=res)
        else:
            log.info("no need to subscribe")
        self.topics = topics


    def validateReadings(self, row):
        '''validate the readings fields'''
        # Test mandatory keys
        incoming  = set(row.keys())
        if not self.MANDATORY_READ <= incoming:
            raise ReadingKeyError(self.MANDATORY_READ - incoming)
        # Mandatory field values
        if not( type(row['name']) == str or type(row['name']) == unicode):
            raise ReadingTypeError('name', str, type(row['name']))
        if type(row['seq']) != int:
            raise ReadingTypeError('seq', int, type(row['seq']))
        if type(row['freq']) != float:
            raise ReadingTypeError('freq', float, type(row['freq']))
        if type(row['mag']) != float:
            raise ReadingTypeError('mag', float, type(row['mag']))
        if type(row['tamb']) != float:
            raise ReadingTypeError('tamb', float, type(row['tamb']))
        if type(row['tsky']) != float:
            raise ReadingTypeError('tsky', float, type(row['tsky']))
        if type(row['rev']) != int:
            raise ReadingTypeError('rev', int, type(row['rev']))
        # optionals field values in Payload V1 format
        if 'az' in row and type(row['az']) != float:
            raise ReadingTypeError('az', float, type(row['az']))
        if 'alt' in row and type(row['alt']) != float:
            raise ReadingTypeError('alt', float, type(row['alt']))
        if 'long' in row and type(row['long']) != float:
            raise ReadingTypeError('long', float, type(row['long']))
        if 'lat' in row and type(row['lat']) != float:
            raise ReadingTypeError('lat', float, type(row['lat']))
        if 'height' in row and type(row['height']) != float:
            raise ReadingTypeError('height', float, type(row['height']))
        if 'wdBm' in row and type(row['wdBm']) != int:
            raise ReadingTypeError('wdBm', int, type(row['wdBm']))


    def validateRegister(self, row):
        '''validate the registration fields'''
        # Test mandatory keys
        incoming  = set(row.keys())
        if not self.MANDATORY_REGR <= incoming:
            raise ReadingKeyError(self.MANDATORY_REGR - incoming)
        # Mandatory field values
        if type(row['rev']) != int:
            raise ReadingTypeError('rev', int, type(row['rev']))
        if not( type(row['name']) == str or type(row['name']) == unicode):
            raise ReadingTypeError('name', str, type(row['name']))
        if not( type(row['mac']) == str or type(row['mac']) == unicode):
            raise ReadingTypeError('mac', str, type(row['mac']))
        if type(row['calib']) != float:
            raise ReadingTypeError('calib', float, type(row['calib']))
        # optionals field values in Payload V1 format
        if 'chan' in row and not (type(row['chan']) == str or type(row['chan']) == unicode):
            raise ReadingTypeError('chan', str, type(row['chan']))


    def handleRegistration(self, row, now):
        '''
        Handle registration data coming from onPublish()
        '''
        self.nregister += 1
        if self.validate:
            try:
                self.validateRegister(row)
                self.handleTimestamps(row, now)
            except ValidationError as e:
                log.error('Validation error in registration payload={payload!s}', payload=row)
                log.error('{excp!s}', excp=e)
            else:
                log.debug('Enque registration from {log_tag} for DB Writter', log_tag=row['name'])
                row['name'] = row['name'].lower()  # Get rid of upper case TESS names
                row['mac']  = row['mac'].upper()   # Ensures MAC address in uppercase
                self.parent.queue['tess_register'].append(row)


    def handleTimestamps(self, row, now):
        '''
        Handle Source timestamp conversions and issues
        '''
        # If not source timestamp then timestamp it and we are done
        if not 'tstamp' in row:
            row['tstamp_src'] = "Subscriber"
            row['tstamp']     = now     # As a datetime instead of string
            log.debug("Adding timestamp data to {log_tag}", log_tag=row['name'])
            return

        row['tstamp_src'] = "Publisher"
        # - This is gonna be awfull with different GPS timestamps ...
        i = 0
        while True:
            try:
                row['tstamp']   = datetime.datetime.strptime(row['tstamp'], TSTAMP_FORMAT[i])
            except ValueError as e:
                i += 1
                log.debug("Trying next timestamp format for {log_tag}", log_tag=row['name'])
                continue
            except IndexError as e:
                raise IncorrectTimestampError(row['tstamp'])
            else:
                break
        delta = math.fabs((now - row['tstamp']).total_seconds())
        if delta > MAX_TSTAMP_OOS:
            log.warn("Publisher {log_tag} timestamp out of sync with Subscriber by {delta} seconds", 
                log_tag=row['name'], delta=delta)


    def handleReadings(self, row, now):
        '''
        Handle actual reqadings data coming from onPublish()
        '''
        self.nreadings += 1
        if self.validate:
            try:
                self.validateReadings(row)
                self.handleTimestamps(row, now)
            except ValidationError as e:
                log.error('Validation error in readings payload={payload!s}', payload=row)
            except IncorrectTimestampError as e:
                log.error("Source timestamp unknown format {tstamp}", tstamp=row['tstamp'])
            except Exception as e:
                log.error('{excp!s}', excp=e)
            else:
                log.debug('Enqueue reading from {log_tag} for DB Writter', log_tag=row['name'])
                row['name'] = row['name'].lower() # Get rid of upper case TESS names
                self.parent.queue['tess_readings'].put(row)


    def onDisconnection(self, reason):
        '''
        Disconenction handler.
        Tells ClientService what to do when the connection is lost
        '''
        log.warn("tessdb lost connection with its MQTT broker")
        self.topics = []
        self.whenConnected().addCallback(self.connectToBroker)


    def onPublish(self, topic, payload, qos, dup, retain, msgId):
        '''
        MQTT Publish message Handler
        '''
        now = datetime.datetime.utcnow()
        self.npublish += 1
        log.debug("payload={payload}", payload=payload)
        try:
            payload = payload.decode('utf-8')  # from bytearray to string
            row = json.loads(payload)
        except Exception as e:
            log.error('Invalid JSON in payload={payload}', payload=payload)
            log.error('{excp!s}', excp=e)
            return

        # Discard retained messages to avoid duplicates in the database
        if retain:
            log.debug('Discarded payload from {log_tag} by retained flag', log_tag=row['name'])
            self.nfilter += 1
            return

        # Apply White List filter
        if len(self.options['tess_whitelist']) and not row['name'] in self.options['tess_whitelist']:
            log.debug('Discarded payload from {log_tag} by whitelist', log_tag=row['name'])
            self.nfilter += 1
            return

        # Apply Black List filter
        if len(self.options['tess_blacklist']) and row['name'] in self.options['tess_blacklist']:
            log.debug('Discarded payload from {log_tag} by blacklist', log_tag=row['name'])
            self.nfilter += 1
            return

        # Handle incoming TESS Data
        topic_part  = topic.split('/')
        
        if self.regAllowed and topic == self.options["tess_topic_register"]:
            self.handleRegistration(row, now)
        elif topic_part[0] in self.tess_heads and topic_part[-1] in self.tess_tails:
            self.handleReadings(row, now)
        else:
            log.warn("message received on unexpected topic {topic}", topic=topic)
