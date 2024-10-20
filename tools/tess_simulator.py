import json
import random

from twisted.logger import Logger
from twisted.internet import reactor, task
from twisted.application.service import Service
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.defer import inlineCallbacks

from mqtt.client.factory import MQTTFactory
from mqtt import v311

from tessdb.logger import startLogging, setLogLevel

NAME = "TESS-SIMULATOR"
MAC = "01:23:45:67:89:AB"
CALIB = 10.0
TX_PERIOD = 5
PROTOCOL_REVISION = 1
TOPIC_REGISTER = "STARS4ALL/register"
TOPIC_READINGS = "STARS4ALL/01/reading"
QoS = 0


class TESS(Service):
    def __init__(self):
        Service.__init__(self)
        self.seq = -1
        self.freq = 4000
        self.mag = 15.0
        self.tamb = 3
        self.tsky = self.tamb - 30

    @inlineCallbacks
    def gotProtocol(self, p):
        log.info("Got protocol")
        self.protocol = p
        kk = yield self.protocol.connect("TwistedMQTT-pub", keepalive=2 * TX_PERIOD, version=v311)
        log.info("connect yielded res={o!s}", o=kk)
        self.protocol.publish(topic=TOPIC_REGISTER, qos=QoS, message=json.dumps(self.register()))
        self.task = task.LoopingCall(self.publish)
        self.task.start(TX_PERIOD, now=False)

    def publish(self):
        self.protocol.publish(topic=TOPIC_READINGS, qos=QoS, message=json.dumps(self.sample()))

    def register(self):
        """
        returns a fake registration payload
        """
        return {"name": NAME, "mac": MAC, "calib": CALIB, "rev": PROTOCOL_REVISION}

    def sample(self):
        """
        returns a fake TESS sample
        """
        self.seq += 1
        self.freq = round(self.freq + random.uniform(-1, 1), 3)
        self.mag = round(self.mag + random.uniform(-0.5, 0.5), 2)
        self.tamb = round(self.tamb + random.uniform(-2, 2), 1)
        self.tsky = self.tamb - 30
        return {
            "seq": self.seq,
            "name": NAME,
            "freq": self.freq,
            "mag": self.mag,
            "tamb": self.tamb,
            "tsky": self.tsky,
            "rev": PROTOCOL_REVISION,
        }


log = Logger()
startLogging()
setLogLevel(namespace=None, levelStr="debug")

factory = MQTTFactory(profile=MQTTFactory.PUBLISHER)
point = TCP4ClientEndpoint(reactor, "test.mosquitto.org", 1883)
tess = TESS()

point.connect(factory).addCallback(tess.gotProtocol)
reactor.run()
