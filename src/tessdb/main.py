# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


# --------------------
# System wide imports
# -------------------

import os
import sys
import argparse

# ---------------
# Twisted imports
# ---------------

from twisted.internet import reactor
from twisted.application.service import IService

# --------------
# local imports
# -------------

from . import __version__
from .config import load_config_file
from .service.relopausable import Application
from .logger import startLogging
from .root.service import TESSDBService
from .dbase.service import DBaseService
from .mqtt.service import MQTTService
from .filter.service import FilterService

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

package = __name__.split(".")[0]

# -------------------
# Auxiliary functions
# -------------------


def valid_file(path):
    """File validator for the command line interface"""
    if not os.path.isfile(path):
        raise IOError(f"Not valid or existing file: {path}")
    return path


def create_parser():
    """
    Create and parse the command line for the tessdb package.
    Minimal options are passed in the command line.
    The rest goes into the config file.
    """
    # -------------------------------
    # Global options to every command
    # -------------------------------

    parser = argparse.ArgumentParser(prog=package, description="TESS Database Server")
    parser.add_argument(
        "--version",
        action="version",
        version="{0} {1}".format(package, __version__),
        help="print version and exit.",
    )
    parser.add_argument("-k", "--console", action="store_true", help="log to console")
    parser.add_argument(
        "-c",
        "--config",
        type=valid_file,
        required=True,
        metavar="<config file>",
        help="detailed configuration file",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        action="store",
        metavar="<log file>",
        help="log file path",
    )
    return parser


def main():
    """The main entry point specified by pyproject.toml"""
    cmdline_opts = create_parser().parse_args()
    config_file = cmdline_opts.config
    options = load_config_file(config_file)

    url = options["dbase"]["connection_string"]
    application = Application("TESSDB")
    tessdbService = TESSDBService(options["tessdb"], config_file)
    tessdbService.setName(TESSDBService.NAME)
    tessdbService.setServiceParent(application)
    dbaseService = DBaseService(url, options["dbase"])
    dbaseService.setName(DBaseService.NAME)
    dbaseService.setServiceParent(tessdbService)
    filterService = FilterService(options["filter"])
    filterService.setName(FilterService.NAME)
    filterService.setServiceParent(tessdbService)
    mqttService = MQTTService(options["mqtt"])
    mqttService.setName(MQTTService.NAME)
    mqttService.setServiceParent(tessdbService)

    # Start the logging subsystem
    startLogging(console=cmdline_opts.console, filepath=cmdline_opts.log_file)
    IService(application).startService()
    reactor.run()
    sys.exit(0)
