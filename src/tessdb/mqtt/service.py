# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import json
import math
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger
from twisted.internet import reactor
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet.endpoints import clientFromString
from twisted.internet.defer import inlineCallbacks

from mqtt.client.factory import MQTTFactory

# --------------
# local imports
# -------------

from tessdb.error import ValidationError, IncorrectTimestampError
from tessdb.logger import setLogLevel
from tessdb.utils import formatted_mac

from tessdb.mqtt import (
    NAMESPACE,
    PROTOCOL_NAMESPACE,
    TESS4C_FILTER_KEYS,
    TESSW_MODEL,
    TESS4C_MODEL,
)
from tessdb.mqtt.validation import (
    validateRegisterTESSW,
    validateReadingsTESSW,
    validateRegisterTESS4C,
    validateReadingsTESS4C,
)

# ----------------
# Module constants
# ----------------

# Reconencting Service. Default backoff policy parameters

INITIAL_DELAY = 4  # seconds
FACTOR = 2
MAX_DELAY = 600  # seconds

# Sequence of possible timestamp formats comming from the Publishers
TSTAMP_FORMAT = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]

# Max Timestamp Ouf-Of-Sync difference, in seconds
MAX_TSTAMP_OOS = 60

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------
# Auxiliar functions
# ------------------


def isTESS4CPayload(row):
    return "F4" in row


def remapTESS4CReadings(row):
    """Flatten the JSON structure for further processing"""
    for i, filt in enumerate(TESS4C_FILTER_KEYS, 1):
        for key, value in row[filt].items():
            row[f"{key}{i}"] = value
    for filt in TESS4C_FILTER_KEYS:
        del row[filt]


def remapTESS4CRegister(row):
    """Flatten the JSON structure for further processing"""
    for i, filt in enumerate(TESS4C_FILTER_KEYS, 1):
        for key, value in row[filt].items():
            row[f"{key}{i}"] = value
    for filt in TESS4C_FILTER_KEYS:
        del row[filt]
    row["model"] = TESS4C_MODEL
    row["nchannels"] = 4


def remapTESSWReadings(row):
    """remaps keywords for the filter/database statges"""
    row["mag1"] = row["mag"]
    row["freq1"] = row["freq"]
    del row["mag"]
    del row["freq"]


def remapTESSWRegister(row):
    """remaps keywords for the filter/database statges"""
    row["calib1"] = row["calib"]
    del row["calib"]
    row["offsethz1"] = row.get("offsethz", 0.0)
    if "offsethz" in row:
        del row["offsethz"]
    row["model"] = TESSW_MODEL
    row["nchannels"] = 1


def handleTimestamps(row, now):
    """
    Handle Source timestamp conversions and issues
    """
    # If not source timestamp then timestamp it and we are done
    if "tstamp" not in row:
        row["tstamp_src"] = "Subscriber"
        row["tstamp"] = now  # As a datetime instead of string
        log.debug("Adding timestamp data to {log_tag}", log_tag=row["name"])
        return
    row["tstamp_src"] = "Publisher"
    # - This is gonna be awfull with different GPS timestamps ...
    i = 0
    # Strips possible trailing Z before the datetime constructor
    row["tstamp"] = row["tstamp"][:-1] if row["tstamp"][-1] == "Z" else row["tstamp"]
    while True:
        try:
            row["tstamp"] = datetime.datetime.strptime(row["tstamp"], TSTAMP_FORMAT[i])
        except ValueError:
            i += 1
            log.debug("Trying next timestamp format for {log_tag}", log_tag=row["name"])
            continue
        except IndexError:
            raise IncorrectTimestampError(row["tstamp"])
        else:
            row["tstamp"] = row["tstamp"].replace(tzinfo=datetime.timezone.utc)
            break
    delta = math.fabs((now - row["tstamp"]).total_seconds())
    if delta > MAX_TSTAMP_OOS:
        log.warn(
            "Publisher {log_tag} timestamp out of sync with Subscriber by {delta} seconds",
            log_tag=row["name"],
            delta=delta,
        )


# -------
# Classes
# -------


class MQTTService(ClientService):
    NAME = "MQTTService"

    # Default subscription QoS

    QoS = 2

    def __init__(self, options, **kargs):
        self.options = options
        self.topics = []
        self.regAllowed = False
        setLogLevel(namespace=NAMESPACE, levelStr=options["log_level"])
        setLogLevel(namespace=PROTOCOL_NAMESPACE, levelStr=options["protocol_log_level"])
        self.tess_heads = [t.split("/")[0] for t in self.options["tess_topics"]]
        self.tess_tails = [t.split("/")[2] for t in self.options["tess_topics"]]
        self.factory = MQTTFactory(profile=MQTTFactory.SUBSCRIBER)
        self.endpoint = clientFromString(reactor, self.options["broker"])
        if self.options["username"] == "":
            self.options["username"] = None
            self.options["password"] = None
        self.resetCounters()
        ClientService.__init__(
            self,
            self.endpoint,
            self.factory,
            retryPolicy=backoffPolicy(
                initialDelay=INITIAL_DELAY, factor=FACTOR, maxDelay=MAX_DELAY
            ),
        )

    # -----------
    # Service API
    # -----------

    def startService(self):
        log.info("Starting MQTT Client Service")
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
        setLogLevel(namespace=NAMESPACE, levelStr=new_options["log_level"])
        setLogLevel(namespace=PROTOCOL_NAMESPACE, levelStr=new_options["protocol_log_level"])
        log.info("new log level is {lvl}", lvl=new_options["log_level"])
        yield self.subscribe(new_options)
        self.options = new_options
        self.tess_heads = [t.split("/")[0] for t in self.options["tess_topics"]]
        self.tess_tails = [t.split("/")[2] for t in self.options["tess_topics"]]

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        """Resets stat counters"""
        self.npublish = 0
        self.nreadings = 0
        self.nregister = 0
        self.nfilter = 0

    def getCounters(self):
        return [self.npublish, self.nreadings, self.nregister, self.nfilter]

    def logCounters(self):
        """log stat counters"""
        # get stats
        result = self.getCounters()
        log.info(
            "MQTT Stats [Total, Reads, Register, Discard] = {counters!s}",
            counters=result,
        )

    # --------------
    # Helper methods
    # ---------------

    @inlineCallbacks
    def connectToBroker(self, protocol):
        """
        Connect to MQTT broker
        """
        self.protocol = protocol
        self.protocol.onPublish = self.onPublish
        self.protocol.onDisconnection = self.onDisconnection

        try:
            client_id = self.options["client_id"]
            yield self.protocol.connect(
                client_id,
                username=self.options["username"],
                password=self.options["password"],
                keepalive=self.options["keepalive"],
            )
            yield self.subscribe(self.options)
        except Exception as e:
            log.error(
                "Connecting to {broker} raised {excp!s}",
                broker=self.options["broker"],
                excp=e,
            )
        else:
            log.info(
                "Connected as client '{id}' and subscribed to '{broker}'",
                id=client_id,
                broker=self.options["broker"],
            )

    @inlineCallbacks
    def subscribe(self, options):
        """
        Smart subscription to a list of (topic, qos) tuples
        """
        # Make the list of tuples first
        topics = [(topic, self.QoS) for topic in options["tess_topics"]]
        if options["tess_topic_register"] != "":
            self.regAllowed = True
            topics.append((options["tess_topic_register"], self.QoS))
        else:
            self.regAllowed = False
        # Unsubscribe first if necessary from old topics
        diff_topics = [t[0] for t in (set(self.topics) - set(topics))]
        if len(diff_topics):
            log.info("Unsubscribing from topics={topics!r}", topics=diff_topics)
            res = yield self.protocol.unsubscribe(diff_topics)
            log.debug("Unsubscription result={result!r}", result=res)
        else:
            log.info("no need to unsubscribe")
        # Now subscribe to new topics
        diff_topics = [t for t in (set(topics) - set(self.topics))]
        if len(diff_topics):
            log.info("Subscribing to topics={topics!r}", topics=diff_topics)
            res = yield self.protocol.subscribe(diff_topics)
            log.debug("Subscription result={result!r}", result=res)
        else:
            log.info("no need to subscribe")
        self.topics = topics

    def handleReadings(self, row, now):
        """
        Handle actual reqadings data coming from onPublish()
        """
        self.nreadings += 1
        try:
            if isTESS4CPayload(row):
                validateReadingsTESS4C(row)
                remapTESS4CReadings(row)
            else:
                validateReadingsTESSW(row)
                remapTESSWReadings(row)
            handleTimestamps(row, now)
        except ValidationError as e:
            log.error("Validation error {excp} in payload {payload}", excp=e, payload=row)
        except IncorrectTimestampError:
            log.error("Source timestamp unknown format {tstamp}", tstamp=row["tstamp"])
        except Exception:
            log.failure(
                "Unexpected exception when dealing with readings {payload}. Stack trace follows:",
                payload=row,
            )
        else:
            # Get rid of upper case TESS names
            row["name"] = row["name"].lower()
            self.parent.queue["tess_readings"].put(row)

    def handleRegistration(self, row, now):
        """
        Handle registration data coming from onPublish()
        """
        log.info("Register message at {now}: {row}", row=row, now=now)
        self.nregister += 1
        try:
            if isTESS4CPayload(row):
                validateRegisterTESS4C(row)
                remapTESS4CRegister(row)
            else:
                # ensure a floating point calibration constant
                row["calib"] = float(row["calib"])
                validateRegisterTESSW(row)
                remapTESSWRegister(row)
            handleTimestamps(row, now)
        except ValidationError as e:
            log.error("Validation error in registration payload={payload!s}", payload=row)
            log.error("{excp!s}", excp=e)
        except Exception:
            log.failure(
                "Unexpected exception When dealing with registration {payload}. Stack trace follows:",
                payload=row,
            )
        else:
            try:
                # Makes sure we have a properly formatted MAC
                row["mac"] = formatted_mac(row["mac"])
            except Exception as e:
                log.error("{excp!s}", excp=e)
            else:
                # Get rid of upper case TESS names
                row["name"] = row["name"].lower()
                self.parent.queue["tess_register"].append(row)

    def onDisconnection(self, reason):
        """
        Disconenction handler.
        Tells ClientService what to do when the connection is lost
        """
        log.warn("tessdb lost connection with its MQTT broker")
        self.topics = []
        self.whenConnected().addCallback(self.connectToBroker)

    def onPublish(self, topic, payload, qos, dup, retain, msgId):
        """
        MQTT Publish message Handler
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        self.npublish += 1
        log.debug("payload={payload}", payload=payload)
        try:
            payload = payload.decode("utf-8")  # from bytearray to string
            row = json.loads(payload)
        except Exception as e:
            log.error("Invalid JSON in payload={payload}", payload=payload)
            log.error("{excp!s}", excp=e)
            return
        # Discard retained messages to avoid duplicates in the database
        if retain:
            log.debug("Discarded payload from {log_tag} by retained flag", log_tag=row["name"])
            self.nfilter += 1
            return
        # Apply White List filter
        if (
            len(self.options["tess_whitelist"])
            and row["name"] not in self.options["tess_whitelist"]
        ):
            log.debug("Discarded payload from {log_tag} by whitelist", log_tag=row["name"])
            self.nfilter += 1
            return
        # Apply Black List filter
        if len(self.options["tess_blacklist"]) and row["name"] in self.options["tess_blacklist"]:
            log.debug("Discarded payload from {log_tag} by blacklist", log_tag=row["name"])
            self.nfilter += 1
            return
        # Handle incoming TESS Data
        topic_part = topic.split("/")
        if self.regAllowed and topic == self.options["tess_topic_register"]:
            self.handleRegistration(row, now)
        elif topic_part[0] in self.tess_heads and topic_part[-1] in self.tess_tails:
            self.handleReadings(row, now)
        else:
            log.warn("message received on unexpected topic {topic}", topic=topic)
