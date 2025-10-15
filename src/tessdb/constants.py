# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

from enum import StrEnum, IntEnum


class MessagePriority(IntEnum):
    """Priority of messages coming from the MQTT broker or the HTTP admin interface"""
    REGISTER = 1
    FILTER_READINGS = 2 # pending readings from filter task to write to database when flushing
    MQTT_READINGS = 3
  
class Topic(StrEnum):
    SERVER_STATS = "server.stats"
    SERVER_RELOAD = "server.reload"
    SERVER_PAUSE = "server.pause"
    SERVER_RESUME = "server.resume"
    SERVER_FLUSH = "server.flush"
    PHOT_LOG_LEVEL = "server.plog_level"
    DATABASE_FLUSH = "database.flush"


DEFAULT_FILTER = "UV/IR-740"
DEFAULT_AZIMUTH = 0.0
DEFALUT_ALTITUDE = 90.0
DEFAULT_FOV = 17.0
DEFAULT_OFFSET_HZ = 0.0

UNKNOWN = "Unknown"
