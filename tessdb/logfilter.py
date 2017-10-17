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
    L{ILogFilterPredicate} that filters out events with a log tag not in a tag set.
    Events that do not have a log_tag key are forwarded to the next filter.
    If the tag set is empty, the events are also forwarded
    """

    def __init__(self, defaultLogTags=[]):
        """
        """
        self.logTags = defaultLogTags


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


__all__ = [
    "LogTagFilterPredicate"
]
