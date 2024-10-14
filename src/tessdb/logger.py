# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


# --------------------
# System wide imports
# -------------------

import sys

# ---------------
# Twisted imports
# ---------------

from zope.interface import implementer

from twisted.logger import (
    LogLevel,
    globalLogBeginner,
    textFileLogObserver,
    FilteringLogObserver,
    LogLevelFilterPredicate,
    ILogFilterPredicate,
    PredicateResult,
)

# --------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

# --------------
# Module Classes
# --------------


@implementer(ILogFilterPredicate)
class LogTagFilterPredicate(object):
    """
    L{ILogFilterPredicate} that filters out events with a log tag not in a tag set.
    Events that do not have a log_tag key are forwarded to the next filter.
    If the tag set is empty, the events are also forwarded
    """

    def __init__(self, defaultLogTags=None):
        """ """
        self.logTags = list() if defaultLogTags is None else defaultLogTags

    def setLogTags(self, logTags):
        """
        Set a new tag set. An iterable (usually a sequence)
        """
        self.logTags = logTags

    def __call__(self, event):
        eventTag = event.get("log_tag", None)

        # Allow events with missing log_tag to pass through
        if eventTag is None:
            return PredicateResult.maybe

        # Allow all events to pass through if empty tag set
        if len(self.logTags) == 0:
            return PredicateResult.maybe

        # Allow events contained in the tag set to pass through
        if eventTag in self.logTags:
            return PredicateResult.maybe

        return PredicateResult.no


# ----------------------------------------------------------------------


# -----------------------
# Module global variables
# -----------------------

# Global object to control globally namespace logging
logLevelFilterPredicate = LogLevelFilterPredicate(defaultLogLevel=LogLevel.info)

# Global object for filtering out events with a log_tag not in a tag set
logTagFilterPredicate = LogTagFilterPredicate()

# ------------------------
# Module Utility Functions
# ------------------------


def startLogging(console=True, filepath=None):
    """
    Starts the global Twisted logger subsystem with maybe
    stdout and/or a file specified in the config file
    """
    global logLevelFilterPredicate
    global logTagFilterPredicate

    observers = []
    if console:
        observers.append(
            FilteringLogObserver(
                observer=textFileLogObserver(sys.stdout),
                predicates=[logTagFilterPredicate, logLevelFilterPredicate],
            )
        )

    if filepath is not None and filepath != "":
        observers.append(
            FilteringLogObserver(
                observer=textFileLogObserver(open(filepath, "a")),
                predicates=[logTagFilterPredicate, logLevelFilterPredicate],
            )
        )
    globalLogBeginner.beginLoggingTo(observers)


def setLogLevel(namespace=None, levelStr="info"):
    """
    Set a new log level for a given namespace
    LevelStr is: 'critical', 'error', 'warn', 'info', 'debug'
    """
    level = LogLevel.levelWithName(levelStr)
    logLevelFilterPredicate.setLogLevelForNamespace(namespace=namespace, level=level)


def setLogTags(logTags):
    """
    Set a new tag set for filtering out events
    """
    logTagFilterPredicate.setLogTags(logTags)


# ----------------------------------------------------------------------


__all__ = [
    "startLogging",
    "setLogLevel",
    "setLogTags",
]
