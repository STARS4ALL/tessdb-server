# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

from collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger
from twisted.internet import task
from twisted.internet.defer import inlineCallbacks, DeferredQueue
from twisted.internet.threads import deferToThread

# --------------
# local imports
# -------------

from tessdb.service.relopausable import MultiService

from tessdb.config import VERSION_STRING, load_config_file
from tessdb.mqtt.service import MQTTService
from tessdb.filter.service import FilterService
from tessdb.dbase.service import DBaseService
from tessdb.logger import setLogLevel, setLogTags

# ----------------
# Module constants
# ----------------

NAMESPACE = "tessdb"

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)


class TESSDBService(MultiService):
    # Service name
    NAME = "TESSDB"

    # Stats period task in seconds
    T_STAT = 3600

    def __init__(self, config_opts, cfgFilePath):
        MultiService.__init__(self)
        self.cfgFilePath = cfgFilePath
        self.queue = {
            "tess_register": deque(),
            "tess_readings": DeferredQueue(),
            "tess_filtered_readings": deque(),
        }
        self.statsTask = task.LoopingCall(self.logCounters)
        setLogLevel(namespace="tessdb", levelStr=config_opts["log_level"])
        setLogTags(logTags=config_opts["log_selected"])

    # -----------
    # Service API
    # -----------

    def startService(self):
        log.info(
            "Starting TessDB {tessdb}, config file '{cfg}'",
            tessdb=VERSION_STRING,
            cfg=self.cfgFilePath,
        )
        self.dbaseService = self.getServiceNamed(DBaseService.NAME)
        self.filterService = self.getServiceNamed(FilterService.NAME)
        self.mqttService = self.getServiceNamed(MQTTService.NAME)
        self.dbaseService.startService()
        self.filterService.startService()
        self.mqttService.startService()
        self.statsTask.start(self.T_STAT, now=False)  # call every T seconds

    def pauseService(self):
        """
        Pause services
        """
        return self.dbaseService.pauseService()

    def resumeService(self):
        """
        Resume services
        """
        return self.dbaseService.resumeService()

    @inlineCallbacks
    def reloadService(self, options):
        """
        Reload service parameters
        """
        log.warn("{tessdb} config being reloaded", tessdb=VERSION_STRING)
        try:
            config_opts = yield deferToThread(load_config_file, self.cfgFilePath)
        except Exception as e:
            log.error("Error trying to reload: {excp!s}", excp=e)
        else:
            level = config_opts["tessdb"]["log_level"]
            setLogLevel(namespace="tessdb", levelStr=level)
            log.info("new log level is {lvl}", lvl=level)
            setLogTags(logTags=config_opts["tessdb"]["log_selected"])
            yield self.mqttService.reloadService(config_opts["mqtt"])
            yield self.filterService.reloadService(config_opts["filter"])
            yield self.dbaseService.reloadService(config_opts["dbase"])

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        """Resets stat counters"""
        self.mqttService.resetCounters()
        self.dbaseService.resetCounters()

    def logCounters(self):
        """log stat counters"""
        self.mqttService.logCounters()
        self.dbaseService.logCounters()
        self.resetCounters()
