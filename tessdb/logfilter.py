# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------


# ---------------
# Twisted imports
# ---------------

from zope.interface import Interface, implementer

from twisted.logger import ILogFilterPredicate, PredicateResult

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------

# --------------
# Module Classes 
# --------------

@implementer(ILogFilterPredicate)
class LogTagFilterPredicate(object):
    """
    L{ILogFilterPredicate} that filters out events with a log level lower than
    the log level for the event's namespace.
    Events that not not have a log level or namespace are also dropped.
    """

    def __init__(self, defaultLogTags=[]):
        """
        """
        self.logTags = defaultLogTags


    def setLogTags(self, logTags):
        """
        """
        self.logTags = logTags


    def __call__(self, event):
        eventTag = event.get("log_tag", None)

        # Allow events with missing log tag to pass through
        if eventTag is None:
            return PredicateResult.maybe

        # Allow all events to pass through if empty tag set
        if len(self.logTags) == 0:
            return PredicateResult.maybe

        # Allow events in the tag set to pass through
        if eventTag in self.logTags:
            return PredicateResult.maybe

        return PredicateResult.no

# ----------------------------------------------------------------------


__all__ = [
    
]
