# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

# ---------------
# Twisted imports
# ---------------

from twisted.internet import task, reactor

#--------------
# local imports
# -------------

from tessdb.service.relopausable import Service, MultiService, Application
from tessdb.logger               import sysLogInfo,  startLogging
from tessdb.config               import VERSION_STRING, cmdline, loadCfgFile
from tessdb.tessdb               import TESSDBService
from tessdb.dbservice            import DBaseService
from tessdb.mqttservice          import MQTTService
from tessdb.filterservice        import FilterService   



# Read the command line arguments and config file options
cmdline_opts = cmdline()
config_file = cmdline_opts.config
if config_file:
   options  = loadCfgFile(config_file)
else:
   options = None

# Start the logging subsystem
startLogging(console=cmdline_opts.console, filepath=cmdline_opts.log_file)

# ------------------------------------------------
# Assemble application from its service components
# ------------------------------------------------

application = Application("TESSDB")

tessdbService  = TESSDBService(options['tessdb'], config_file)
tessdbService.setName(TESSDBService.NAME)
tessdbService.setServiceParent(application)

dbaseService = DBaseService(options['dbase'])
dbaseService.setName(DBaseService.NAME)
dbaseService.setServiceParent(tessdbService)

filterService = FilterService(options['filter'])
filterService.setName(FilterService.NAME)
filterService.setServiceParent(tessdbService)

mqttService = MQTTService(options['mqtt'])
mqttService.setName(MQTTService.NAME)
mqttService.setServiceParent(tessdbService)

# --------------------------------------------------------
# Store direct links to subservices in our manager service
# --------------------------------------------------------


__all__ = [ "application" ]