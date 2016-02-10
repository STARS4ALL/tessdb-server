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

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task
from twisted.application.service import Service
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.defer import inlineCallbacks

from mqtt import v311
from mqtt.client.factory import MQTTFactory

#--------------
# local imports
# -------------

from .error import ValidationError, ReadingKeyError, ReadingTypeError
from .logger import setLogLevel
from .utils  import chop

# ----------------
# Module constants
# ----------------

NSTATS = 100

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='mqtt')

class MQTTService(Service):

    # Default subscription QoS
    
    QoS = 2
    
    # Mandatory keys in each register
    MANDATORY_REGR = set(['name','mac','calib'])
    
    # Mandatory keys in each reading
    MANDATORY_READ = set(['seq','name','freq','mag','tamb','tsky'])

    def __init__(self, parent, options, **kargs):
        Service.__init__(self)
        self.parent     = parent
        self.options    = options
        self.topics     = []
        self.regAllowed = False
        self.nregister  = 0
        self.nreadings  = 0
        self.npublish   = 0
        self.validate   = options['validation']
        setLogLevel(namespace='mqtt', levelStr=options['log_level'])

        self.tess_heads  = [ t.split('/')[0] for t in self.options['tess_topics'] ]
        self.tess_tails  = [ t.split('/')[2] for t in self.options['tess_topics'] ]
    
    def startService(self):
        log.info("starting MQTT Client Service")
        self.factory  = MQTTFactory(profile=MQTTFactory.SUBSCRIBER)
        self.endpoint = TCP4ClientEndpoint(reactor, self.options['broker'], self.options['port'])
        self.endpoint.connect(self.factory).addCallback(self.connectToBroker)
        Service.startService(self)

    def stopService(self):
        Service.stopService()

    #---------------------
    # Extended Service API
    # --------------------

    @inlineCallbacks
    def reloadService(self, new_options):
        self.validate  = new_options['validation']
        setLogLevel(namespace='mqtt', levelStr=new_options['log_level'])
        log.info("new log level is {lvl}", lvl=new_options['log_level'])
        yield self.subscribe(new_options)
        self.options = new_options
        self.tess_heads  = [ t.split('/')[0] for t in self.options['tess_topics'] ]
        self.tess_tails  = [ t.split('/')[2] for t in self.options['tess_topics'] ]

    def pauseService(self):
        pass

    def resumeService(self):
        pass

    # --------------
    # Helper methods
    # ---------------
   
    @inlineCallbacks
    def connectToBroker(self, protocol):
        '''
        Connect to MQTT broker
        '''
        log.debug("Got protocol 1")
        self.protocol = protocol
        self.protocol.setPublishHandler(self.onPublish)
        log.debug("Got protocol 2")
        yield self.protocol.connect("TwistedMQTT-subs", keepalive=self.options['keepalive'])
        log.info("Connected to {broker} on port {port}", broker=self.options['broker'], port=self.options['port'])
        yield self.subscribe(self.options)

    @inlineCallbacks
    def subscribe(self, options):
        '''
        Smart subscription to a list of (topic, qos) tuples
        '''
        # Make the list of tuples first
        topics = [ (topic, self.QoS) for topic in options['tess_topics'] ]
        if options['topic_register'] != "":
            self.regAllowed = True
            topics.append( (options['topic_register'], self.QoS) )
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
            raise ReadingKeyError(self.MANDATORY - incoming)
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

    def validateRegister(self, row):
        '''validate the registration fields'''
        # Test mandatory keys
        incoming  = set(row.keys())
        if not self.MANDATORY_REGR <= incoming:
            raise ReadingKeyError(self.MANDATORY - incoming)
        # Mandatory field values
        if not( type(row['name']) == str or type(row['name']) == unicode):
            raise ReadingTypeError('name', str, type(row['name']))
        if not( type(row['mac']) == str or type(row['mac']) == unicode):
            raise ReadingTypeError('mac', str, type(row['mac']))
        if type(row['calib']) != float:
            raise ReadingTypeError('calib', float, type(row['calib']))
        # optionals field values in Payload V1 format
        if 'channel' in row and type(row['channel']) != float:
            raise ReadingTypeError('channel', float, type(row['channel']))


    def logStats(self):
        '''
        Log basic stats on received messages
        '''
        if self.npublish % NSTATS == 0:
            log.info("(Total/Readings/Registrations) = ({total}/{nreadings}/{nregister})", 
                total=self.npublish, nreadings=self.nreadings, nregister=self.nregister)


    def onPublish(self, topic, payload, qos, dup, retain, msgId):
        '''
        MQTT Pubish message Handler
        '''
        now = datetime.datetime.utcnow()
        self.npublish += 1
        log.debug("topic={topic}, payload={payload} qos={qos}, dup={dup} retain={retain}, msgId={id}", 
            topic=topic, payload=payload, qos=qos, dup=dup, retain=retain, id=msgId)
        try:
            payload = str(payload)  # from bytearray to string
            row = json.loads(payload)
        except Exception as e:
            log.error('Invalid JSON in payload={payload}', payload=payload)
            log.error('{excp!r}', excp=e)
            return
        row['tstamp'] = now     # As a datetime instead of string

        # Handle incoming TESS Data
        topic_part  = topic.split('/')

        if topic_part[0] in self.tess_heads and topic_part[2] in self.tess_tails:
            self.nreadings += 1
            if self.validate:
                try:
                    self.validateReadings(row)
                except ValidationError as e:
                    log.error('Validation error in readings payload={payload!s}', payload=row)
                    log.error('{excp!r}', excp=e)
                    return
            self.parent.queue['tess_readings'].append(row)
        elif self.regAllowed and topic == self.options["tess_topic_register"]:
            self.nregister += 1
            if self.validate:
                try:
                    self.validateRegister(row)
                except ValidationError as e:
                    log.error('Validation error in registration payload={payload!s}', payload=row)
                    log.error('{excp!r}', excp=e)
                    return
            self.parent.queue['tess_register'].append(row)
        else:
            log.warn("message received on unexpected topic {topic}", topic=topic)
        self.logStats()
