# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2016 Rafael Gonzalez.
#
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

# --------------
# local imports
# -------------

from . import NAMESPACE

# -----------------------
# Module Global Variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------


def roundDateTime(ts, secs_resol):
    """Round a timestamp to the nearest minute"""
    if secs_resol > 1:
        tsround = ts + datetime.timedelta(seconds=0.5 * secs_resol)
    else:
        tsround = ts
    time_id = tsround.hour * 10000 + tsround.minute * 100 + tsround.second
    date_id = tsround.year * 10000 + tsround.month * 100 + tsround.day
    return date_id, time_id
