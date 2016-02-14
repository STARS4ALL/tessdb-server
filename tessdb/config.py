# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys
import os
import os.path
import argparse
import errno

# Only Python 2
import ConfigParser

# ---------------
# Twisted imports
# ---------------

from twisted.logger import LogLevel

#--------------
# local imports
# -------------

from .utils import chop
from . import __version__

# ----------------
# Module constants
# ----------------


VERSION_STRING = "tessdb/{0}/Python {1}.{2}".format(__version__, sys.version_info.major, sys.version_info.minor)

# Default config file path
if os.name == "nt":
    CONFIG_FILE=os.path.join("C:\\", "tessdb", "config", "config.ini")
else:
    CONFIG_FILE="/etc/tessdb/config"


# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------

def cmdline():
    '''
    Create and parse the command line for the tessdb package.
    Minimal options are passed in the command line.
    The rest goes into the config file.
    '''
    parser = argparse.ArgumentParser(prog='tessdb')
    parser.add_argument('--version',            action='version', version='{0}'.format(VERSION_STRING))
    parser.add_argument('-k' , '--console',     action='store_true', help='log to console')
    parser.add_argument('-i' , '--interactive', action='store_true', help='run in foreground (Windows only)')
    parser.add_argument('-c' , '--config', type=str,  action='store', metavar='<config file>', help='detailed configuration file')
    parser.add_argument('-s' , '--startup', type=str, action='store', metavar='<auto|manual>', help='Windows service starup mode')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(' install', type=str, nargs='?', help='install Windows service')
    group.add_argument(' start',   type=str, nargs='?', help='start Windows service')
    group.add_argument(' stop',    type=str, nargs='?', help='start Windows service')
    group.add_argument(' remove',  type=str, nargs='?', help='remove Windows service')
    return parser.parse_args()


def loadCfgFile(path):
    '''
    Load options from configuration file whose path is given
    Returns a dictionary
    '''

    if path is None or not (os.path.exists(path)):
        raise IOError(errno.ENOENT,"No such file or directory", path)

    options = {}
    parser  =  ConfigParser.RawConfigParser()
    # str is for case sensitive options
    #parser.optionxform = str
    parser.read(path)

    options['tessdb'] = {}
    options['tessdb']['log_level']  = parser.get("tessdb","log_level")

    options['log'] = {}
    options['log']['path']     = parser.get("log","path")
    options['log']['policy']   = parser.get("log","policy")
    options['log']['max_size'] = parser.getint("log","max_size")

    options['mqtt'] = {}
    options['mqtt']['log_level']      = parser.get("mqtt","log_level")
    options['mqtt']['validation']     = parser.getboolean("mqtt","validation")
    options['mqtt']['broker']         = parser.get("mqtt","broker")
    options['mqtt']['port']           = parser.getint("mqtt","port")
    options['mqtt']['keepalive']      = parser.getint("mqtt","keepalive")
    options['mqtt']['tess_topics']    = chop(parser.get("mqtt","tess_topics"),',')
    options['mqtt']['tess_topic_register'] = parser.get("mqtt","tess_topic_register")

    options['dbase'] = {}
    options['dbase']['log_level']         = parser.get("dbase","log_level")
    options['dbase']['type']              = parser.get("dbase","type")
    options['dbase']['connection_string'] = parser.get("dbase","connection_string")
    options['dbase']['json_dir']          = parser.get("dbase","json_dir")
    options['dbase']['year_start']        = parser.getint("dbase","year_start")
    options['dbase']['year_end']          = parser.getint("dbase","year_end")
    options['dbase']['date_fmt']          = parser.get("dbase","date_fmt")

    return options


__all__ = [VERSION_STRING, loadCfgFile, cmdline]
