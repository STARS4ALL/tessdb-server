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

from twisted import __version__ as __twisted_version__

# ---------------------
# Third party libraries
# ---------------------

from environs import Env
import tomli

# --------------
# local imports
# -------------

from ._version import __version__

# ----------------
# Module constants
# ----------------

VERSION_STRING = "{0} on Twisted {1}, Python {2}.{3}".format(
    __version__, __twisted_version__, sys.version_info.major, sys.version_info.minor
)


CONFIG_FILE = "/etc/tessdb/config.toml"


# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------


def load_config_file(path):
    """
    Load options from configuration file whose path is given
    Returns a dictionary
    """

    with open(path, "rb") as config_file:
        options = tomli.load(config_file)

    env = Env()
    # An .enf file is usefu only for development
    # donot rely on it for systemd service
    env.read_env()  # read .env file, if one exists

    options["mqtt"]["broker"] = env.str("MQTT_BROKER")
    options["mqtt"]["username"] = env.str("MQTT_USERNAME")
    options["mqtt"]["password"] = env.str("MQTT_PASSWORD")
    options["mqtt"]["client_id"] = env.str("MQTT_CLIENT_ID")
    options["dbase"]["connection_string"] = env.str("DATABASE_URL")

    return options


__all__ = [
    "VERSION_STRING",
    "load_config_file",
]
