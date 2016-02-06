# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------


# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet.defer import inlineCallbacks
from twisted.enterprise import adbapi

#--------------
# local imports
# -------------


from .date       import Date
from .time       import TimeOfDay
from .units      import Units
from .location   import Location
from .instrument import Instrument
from .readings   import Readings

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
      kargs['check_same_thread']=False
      self.pool = adbapi.ConnectionPool("sqlite3", *args, **kargs)
      self.instruments = Instrument(self.pool)
      self.units       = Units(self.pool)
      self.readings    = Readings(self.pool, self)

   # ---------------------
   # SCHEMA GENERATION API
   # ---------------------

   @inlineCallbacks
   def schema(self, json_dir, date_fmt, year_start, year_end, replace=False):
      '''
      Schema Generation
      Returns a Deferred
      '''
      yield Date(self.pool).schema(date_fmt, year_start, year_end, replace)
      yield TimeOfDay(self.pool).schema(json_dir, replace)
      yield Location(self.pool).schema(json_dir, replace)
      yield self.instruments.schema(json_dir, replace)
      yield self.units.schema(json_dir, replace)
      yield self.readings.schema(json_dir, replace)

   # ---------------
   # OPERATIONAL API
   # ---------------

   def register(self, row):
      '''
      Registers an instrument given its MAC address, friendly name and calibration constant.
      Returns a Deferred
      '''
      return self.instruments.register(row)

   def update(self, row):
      '''
      Update readngs table
      Returns a Deferred 
      '''
      return self.readings.update(row)

  