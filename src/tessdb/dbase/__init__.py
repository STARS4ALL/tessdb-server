# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

import datetime

# ---------------------
# Subppackage Constants
# ---------------------

NAMESPACE = "dbase"

DEFAULT_FILTER = "UV/IR-740"
DEFAULT_AZIMUTH = 0.0
DEFALUT_ALTITUDE = 90.0
DEFAULT_FOV = 17.0
DEFAULT_OFFSET_HZ = 0.0

UNKNOWN = "Unknown"
EXPIRED = "Expired"
CURRENT = "Current"
AUTOMATIC = "Automatic"  # Value for the registered column
INFINITE_TIME = datetime.datetime(
    year=2999,
    month=12,
    day=31,
    hour=23,
    minute=59,
    second=59,
    tzinfo=datetime.timezone.utc,
)
