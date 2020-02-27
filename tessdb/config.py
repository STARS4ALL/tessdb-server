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

try:
    # Python 2
    import ConfigParser
except:
    import configparser as ConfigParser

# ---------------
# Twisted imports
# ---------------


from twisted  import __version__ as __twisted_version__

#--------------
# local imports
# -------------

from .logger import LogLevel
from .utils  import chop
from . import __version__

# ----------------
# Module constants
# ----------------

VERSION_STRING = "{0} on Twisted {1}, Python {2}.{3}".format(__version__, __twisted_version__, sys.version_info.major, sys.version_info.minor)

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
    parser.add_argument('-v' , '--version',     action='version', version='{0}'.format(VERSION_STRING), help='print version and exit.')
    parser.add_argument('-k' , '--console',     action='store_true', help='log to console')
    parser.add_argument('-i' , '--interactive', action='store_true', help='run in foreground (Windows only)')
    parser.add_argument('-c' , '--config',  type=str,  action='store', metavar='<config file>', help='detailed configuration file')
    parser.add_argument('-s' , '--startup', type=str, action='store', metavar='<auto|manual>', help='Windows service starup mode')
    parser.add_argument('--log-file',       type=str, default=None,    action='store', metavar='<log file>', help='log file path')
  
    
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
    options['tessdb']['log_selected']   = chop(parser.get("tessdb","log_selected"),',')

    options['mqtt'] = {}
    options['mqtt']['log_level']      = parser.get("mqtt","log_level")
    options['mqtt']['protocol_log_level'] = parser.get("mqtt","protocol_log_level")
    options['mqtt']['validation']     = parser.getboolean("mqtt","validation")
    options['mqtt']['broker']         = parser.get("mqtt","broker")
    options['mqtt']['username']       = parser.get("mqtt","username")
    options['mqtt']['password']       = parser.get("mqtt","password")
    options['mqtt']['keepalive']      = parser.getint("mqtt","keepalive")
    options['mqtt']['tess_whitelist'] = chop(parser.get("mqtt","tess_whitelist"),',')
    options['mqtt']['tess_blacklist'] = chop(parser.get("mqtt","tess_blacklist"),',')
    options['mqtt']['tess_topics']    = chop(parser.get("mqtt","tess_topics"),',')
    options['mqtt']['tess_topic_register'] = parser.get("mqtt","tess_topic_register")

    options['dbase'] = {}
    options['dbase']['log_level']         = parser.get("dbase","log_level")
    options['dbase']['register_log_level'] = parser.get("dbase","register_log_level")
    options['dbase']['type']              = parser.get("dbase","type")
    options['dbase']['connection_string'] = parser.get("dbase","connection_string")
    options['dbase']['close_when_pause']  = parser.getboolean("dbase","close_when_pause")
    options['dbase']['year_start']        = parser.getint("dbase","year_start")
    options['dbase']['year_end']          = parser.getint("dbase","year_end")
    options['dbase']['date_fmt']          = parser.get("dbase","date_fmt")
    options['dbase']['secs_resolution']   = parser.getint("dbase","secs_resolution")
    options['dbase']['auth_filter']       = parser.getboolean("dbase","auth_filter")

    options['filter'] = {}
    options['filter']['enabled']   = parser.getboolean("filter","enabled")
    options['filter']['depth']     = parser.getint("filter","depth")
    options['filter']['log_level'] = parser.get("filter","log_level")


    return options


__all__ = [
    "VERSION_STRING", 
    "loadCfgFile", 
    "cmdline",
]
