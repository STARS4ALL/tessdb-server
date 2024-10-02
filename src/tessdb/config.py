# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import sys
import os
import os.path
import argparse
import errno

try:
    # Python 2
    import ConfigParser
except:
    import configparser as ConfigParser

# ---------------
# Twisted imports
# ---------------


from twisted import __version__ as __twisted_version__

# --------------
# local imports
# -------------

from .logger import LogLevel
from .utils import chop
from ._version import __version__

# ----------------
# Module constants
# ----------------

VERSION_STRING = "{0} on Twisted {1}, Python {2}.{3}".format(
    __version__, __twisted_version__, sys.version_info.major, sys.version_info.minor)

# Default config file path
if os.name == "nt":
    CONFIG_FILE = os.path.join("C:\\", "tessdb", "config", "config.ini")
else:
    CONFIG_FILE = "/etc/tessdb/config"


# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------


def load_config_file(path):
    '''
    Load options from configuration file whose path is given
    Returns a dictionary
    '''

    if path is None or not (os.path.exists(path)):
        raise IOError(errno.ENOENT, "No such file or directory", path)

    options = {}
    parser = ConfigParser.RawConfigParser()
    # str is for case sensitive options
    #parser.optionxform = str
    parser.read(path)

    options['tessdb'] = {}
    options['tessdb']['log_level'] = parser.get("tessdb", "log_level")
    options['tessdb']['log_selected'] = chop(
        parser.get("tessdb", "log_selected"), ',')

    options['mqtt'] = {}
    options['mqtt']['log_level'] = parser.get("mqtt", "log_level")
    options['mqtt']['protocol_log_level'] = parser.get(
        "mqtt", "protocol_log_level")
    options['mqtt']['broker'] = parser.get("mqtt", "broker")
    options['mqtt']['username'] = parser.get("mqtt", "username")
    options['mqtt']['password'] = parser.get("mqtt", "password")
    options['mqtt']['client_id'] = parser.get("mqtt", "client_id")
    options['mqtt']['keepalive'] = parser.getint("mqtt", "keepalive")
    options['mqtt']['tess_whitelist'] = chop(
        parser.get("mqtt", "tess_whitelist"), ',')
    options['mqtt']['tess_blacklist'] = chop(
        parser.get("mqtt", "tess_blacklist"), ',')
    options['mqtt']['tess_topics'] = chop(
        parser.get("mqtt", "tess_topics"), ',')
    options['mqtt']['tess_topic_register'] = parser.get(
        "mqtt", "tess_topic_register")

    options['dbase'] = {}
    options['dbase']['log_level'] = parser.get("dbase", "log_level")
    options['dbase']['register_log_level'] = parser.get(
        "dbase", "register_log_level")
    options['dbase']['connection_string'] = parser.get(
        "dbase", "connection_string")
    options['dbase']['secs_resolution'] = parser.getint(
        "dbase", "secs_resolution")
    options['dbase']['buffer_size'] = parser.getint("dbase", "buffer_size")
    options['dbase']['auth_filter'] = parser.getboolean("dbase", "auth_filter")
    options['dbase']['zp_threshold'] = parser.getfloat("dbase", "zp_threshold")

    options['filter'] = {}
    options['filter']['enabled'] = parser.getboolean("filter", "enabled")
    options['filter']['depth'] = parser.getint("filter", "depth")
    options['filter']['log_level'] = parser.get("filter", "log_level")

    return options


__all__ = [
    "VERSION_STRING",
    "load_config_file",
    "cmdline",
]
