# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------


import tabulate

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet.defer import inlineCallbacks
from twisted.enterprise import adbapi

#--------------
# local imports
# -------------


from .date          import Date
from .time          import TimeOfDay
from .tess_units    import TESSUnits
from .location      import Location
from .tess          import TESS
from .tess_readings import TESSReadings

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='dbase')

# ==========
# DBASE Class
# ==========


class DBase(object):
   '''
   Facade objet that:
   1) hides all other dbase objects
   2) Serves as a mediator between some of them
   '''

   def __init__(self, *args, **kargs):

      # This is the only reason I keep it as a class and not merge with DB service 
      kargs['check_same_thread']=False
      self.pool          = adbapi.ConnectionPool("sqlite3", *args, **kargs)
      self.tess          = TESS(self.pool)
      self.tess_units    = TESSUnits(self.pool)
      self.tess_readings = TESSReadings(self.pool, self)
      self.tess_locations = Location(self.pool)
      self.date           = Date(self.pool)
      self.time           = TimeOfDay(self.pool)

   # ---------------------
   # SCHEMA GENERATION API
   # ---------------------

   @inlineCallbacks
   def schema(self, json_dir, date_fmt, year_start, year_end, location_filter, location_horizon, replace):
      '''
      Schema Generation
      Returns a Deferred
      '''
      self.tess_readings.setOptions(location_filter, location_horizon)
      yield self.date.schema(date_fmt, year_start, year_end, replace)
      yield self.time.schema(json_dir, replace)
      yield self.tess_locations.schema(json_dir, replace)
      yield self.tess.schema(json_dir, replace)
      yield self.tess_units.schema(json_dir, replace)
      yield self.tess_readings.schema(json_dir, replace)

   # ---------------
   # OPERATIONAL API
   # ---------------

   def register(self, row):
      '''
      Registers an instrument given its MAC address, friendly name and calibration constant.
      Returns a Deferred
      '''
      return self.tess.register(row)

   def update(self, row):
      '''
      Update readngs table
      Returns a Deferred 
      '''
      return self.tess_readings.update(row)

   # -----------
   # Control API
   # -----------
   
   @inlineCallbacks
   def reload(self, json_dir, date_fmt, year_start, year_end, location_filter, location_horizon, replace):
      '''
      Reload configuration.
      Returns a Deferred
      '''
      self.tess_readings.setOptions(location_filter, location_horizon)
      yield self.date.populate(json_dir, replace)
      yield self.tess_locations.populate(json_dir, replace)
      yield self.tess_units.populate(json_dir, replace)
      yield self.tess.populate(json_dir, replace)


   # -------------
   # log stats API
   # -------------

   def resetCounters(self):
      '''Resets stat counters'''
      self.tess_readings.resetCounters()
      self.tess.resetCounters()


   def logCounters(self):
      '''log stat counters'''
      result = self.tess_readings.getCounters()
      text = tabulate.tabulate([result], headers=['Total','Not Registered','Lack Sunrise','Daytime','Dupl','Other'], tablefmt='grid')
      log.info("\n{table}",table=text)
      result = self.tess.getCounters()
      text = tabulate.tabulate([result], headers=['Total','Created','Upd Name','Upd Calib','No Upd Name','No Create Name'], tablefmt='grid')
      log.info("\n{table}",table=text)

