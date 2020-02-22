# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import os
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.internet         import defer
from twisted.internet.defer   import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from twisted.logger           import Logger

#--------------
# local imports
# -------------

from tessdb.sqlite3.utils import Table, TSTAMP_FORMAT, INFINITE_TIME, EXPIRED, CURRENT
from tessdb.error import ReadingKeyError, ReadingTypeError

# ----------------
# Module Constants
# ----------------

# No pre-registerd instruments by default
DEFAULT_INSTRUMENT = []

# No predefined deployment of TESS instruments to Loacations
DEFAULT_DEPLOYMENT = []

# Value for the registered column
AUTOMATIC = "Automatic"

# -----------------------
# Module Global Variables
# -----------------------

log  = Logger(namespace='dbase')
log2 = Logger(namespace='registry')


# ------------------------
# Module Utility Functions
# ------------------------


# ============================================================================ #
#                              TESS INSTRUMENT TABLE (DIMENSION)
# ============================================================================ #

class TESS(Table):

    DEPL_FILE        = 'tess_location.json'
    INSTRUMENTS_FILE = 'tess.json'

    def __init__(self, connection, validate=False):
        Table.__init__(self, connection)
        self.resetCounters()
        self._cache = dict()

    def table(self):
        '''
        Create the SQLite Units table.
        '''
        log.info("Creating tess_t Table if not exists")
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS tess_t
            (
            tess_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address   TEXT, 
            zero_point    REAL,
            filter        TEXT DEFAULT 'UV/IR-cut',
            valid_since   TEXT,
            valid_until   TEXT,
            valid_state   TEXT,
            location_id   INTEGER NOT NULL DEFAULT -1 REFERENCES location_t(location_id),
            model         TEXT    DEFAULT 'TESS-W',
            firmware      TEXT    DEFAULT '1.0',
            channel       INTEGER DEFAULT 0,
            cover_offset  REAL    DEFAULT 0.0,
            fov           REAL    DEFAULT 17.0,
            azimuth       REAL    DEFAULT 0.0,
            altitude      REAL    DEFAULT 90.0,
            authorised    INTEGER DEFAULT 0,
            registered    TEXT    DEFAULT 'Unknown'
            );
            '''
        )

        # It seems that it is no longer true that a given tess name identifies
        # a given TESS-W device. The MAC address is the only vaild identifier 
        # for the device.
        # If a TESS-W is broken, the customer wants to maintain its name.
        # We must build and maintain an associative table from name to MAC Addresses.
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS name_to_mac_t
            (
            name          TEXT NOT NULL,
            mac_address   TEXT NOT NULL REFERENCES tess_t(mac_address), 
            valid_since   TEXT NOT NULL,
            valid_until   TEXT NOT NULL,
            valid_state   TEXT NOT NULL
            );
            '''
        )
        self.connection.commit()

    def indices(self):
        '''
        Create indices to SQLite Units table.
        '''
        log.info("Creating tess_t Indexes if not exists")
        cursor = self.connection.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS tess_mac_i ON tess_t(mac_address);")
        # For the associative table
        cursor.execute("CREATE INDEX IF NOT EXISTS name_to_mac_i ON name_to_mac_t(name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS mac_to_name_i ON name_to_mac_t(mac_address);")
        self.connection.commit()


    def views(self):
        '''
        Create Views associated to this dimension.
        '''
        log.info("Creating tess_t Views if not exists")
        self.connection.execute(
            '''
            CREATE VIEW IF NOT EXISTS tess_v 
            AS SELECT
                tess_t.tess_id,
                name_to_mac_t.name,
                tess_t.channel,
                tess_t.model,
                tess_t.firmware,
                tess_t.mac_address,
                tess_t.zero_point,
                tess_t.cover_offset,
                tess_t.filter,
                tess_t.fov,
                tess_t.azimuth,
                tess_t.altitude,
                tess_t.valid_since,
                tess_t.valid_until,
                tess_t.valid_state,
                tess_t.authorised,
                tess_t.registered,
                location_t.contact_name,
                location_t.organization,
                location_t.contact_email,
                location_t.site,
                location_t.longitude,
                location_t.latitude,
                location_t.elevation,
                location_t.zipcode,
                location_t.location,
                location_t.province,
                location_t.country,
                location_t.timezone,
                location_t.sunrise,
                location_t.sunset
            FROM tess_t 
            JOIN location_t    USING (location_id)
            JOIN name_to_mac_t USING (mac_address)
            WHERE name_to_mac_t.valid_state == "Current";
            '''
        )
        self.connection.commit()


    def populate(self):
        '''
        Populate the SQLite Instruments Table.
        '''
        log.warn("Not populating instruments table from files anymore.")
        

    # --------------
    # Cache handling
    # --------------

    def invalidCache(self, name=None):
        '''Invalid TESS names cache'''
        if name is None:
            log.info("tess_t cache invalidated with size = {size}", size=len(self._cache))
            self._cache = dict()
        elif name in self._cache:
            log.info("tess_t cache selective invalidataion for name {log_tag}", log_tag=name)
            del self._cache[name]

    def updateCache(self, resultset, name):
        '''Update TESS names cache if found'''
        if(len(resultset)):
            self._cache[name] = resultset
        return resultset

    # -------------
    # log stats API
    # -------------

    def resetCounters(self):
        '''Resets stat counters'''
        self.nRegister = 0
        self.nCreation = 0
        self.nRename   = 0
        self.nReplace  = 0
        self.nOverriden = 0
        self.nZPChange = 0
        self.nReboot   = 0

    def getCounters(self):
        '''get stat counters'''
        return (    
                    "[Total, New, Rebooted, Renamed, ZP Changed, Replaced, Overriden]",
                    [
                        self.nRegister, 
                        self.nCreation,
                        self.nReboot,
                        self.nRename, 
                        self.nZPChange, 
                        self.nReplace, 
                        self.nOverriden,
                    ]
                )

    # =======
    # OPERATIONAL API
    # =======

    # ----------------------------
    # Instrument registration (NEW)
    # ----------------------------

    @inlineCallbacks
    def register(self, row):
        '''
        Registers an instrument given its MAC address, friendly name and calibration constant
        Returns a Deferred.
        '''
        log2.debug("New registration request for {log_tag} (maybe not accepted) with data {row}", row=row, log_tag=row['name'])
        self.nRegister += 1

        # Adding extra metadadta for all create/update operations
        row['eff_date']      = row['tstamp'].replace(microsecond=0)
        row['exp_date']      = INFINITE_TIME
        row['valid_expired'] = EXPIRED
        row['valid_current'] = CURRENT
        row['registered']    = AUTOMATIC

        mac  = yield self.lookupMAC(row)    # Returns list of pairs (MAC, name)
        name = yield self.lookupName(row)   # Returns list of pairs (name, MAC)

        log2.debug("self.lookupMAC(row) yields {mac}", mac=mac)
        log2.debug("self.lookupName(row) yields {name}",name=name)

        if not len(mac) and not len(name):
            # Brand new TESS-W case:
            # No existitng (MAC, name) pairs in the name_to_mac_t table
            log2.debug("Registering Brand new photometer: {log_tag} (MAC = {mac})", log_tag=row['name'], mac=row['mac'])
            yield self.addBrandNewTess(row)
            self.nCreation += 1
            log2.info("Brand new photometer registered: {log_tag} (MAC = {mac})", log_tag=row['name'], mac=row['mac'])
        elif len(mac) and not len(name):
            # A clean rename with no collision
            # A (MAC, name) exists in the name_to_mac_t table with the MAC given by the regisitry message
            # but the name in the regisitry message does not.
            oldname = mac[0][1]
            log2.debug("Renaming photometer {oldname} (MAC = {mac}) with brand new name {log_tag}", oldname=oldname, log_tag=row['name'], mac=row['mac'])
            yield self.renamingAssociation(row)
            self.invalidCache(oldname)
            self.nRename += 1
            log2.info("Renamed photometer {oldname} (MAC = {mac}) with brand new name {log_tag}", oldname=oldname, log_tag=row['name'], mac=row['mac'])
        elif not len(mac) and len(name):
            # A (NAC, name) pair exisst in the name_to_mac_t table with the same name as the registre message
            # but the MAC in the registry message is new.
            # This means that we are probably replacing a new photometer but keeping the same name.
            oldmac = name[0][1]
            log2.debug("Replacing photometer tagged {log_tag} (old MAC = {oldmac}) with new one with MAC {mac}", oldmac=oldmac, log_tag=row['name'], mac=row['mac']) 
            yield self.newTessReplacingBroken(row)
            self.invalidCache(row['name'])
            self.nReplace += 1
            log2.info("Replaced photometer tagged {log_tag} (old MAC = {oldmac}) with new one with MAC {mac}", oldmac=oldmac, log_tag=row['name'], mac=row['mac']) 
        else:
            mac  = mac[0]
            name = name[0]
            row['prev_mac']  = name[1]  # MAC not from the register message, but associtated to existing name
            row['prev_name'] = mac[1]   # name not from from the register message, but assoctiated to to existing MAC
            # If the same MAC and same name remain, we must examine if there
            # is a change in the photometer managed attributes (zero_point)
            if row['name'] == row['prev_name'] and row['mac'] == row['prev_mac']:
                yield self.maybeUpdateManagedAttributes(row)
            else:
                # The complex scenario is that two (MAC, name) pairs exists in the name_to_mac_t table
                # In one pair, the MAC is the same as the registry message
                # The other pair has the same name as the registry message
                # So we must invalidate both existing pairs and create a new one
                # The name not coming in the message will get unassigned to a photometer.
                # Renaming with side effects.
                log2.debug("Overriding associations ({n1} -> {m1}) and ({n2} -> {m2}) with new ({log_tag} -> {m}) association data",
                    m=row['mac'], log_tag=row['name'], m1=mac[0], n1=row['prev_name'], m2=row['prev_mac'], n2=name[0])
                yield self.overrideAssociations(row)
                self.invalidCache(row['name'])
                self.invalidCache(row['prev_name'])
                self.nOverriden += 1
                log2.info("Overridden associations ({n1} -> {m1}) and ({n2} -> {m2}) with new ({log_tag} -> {m}) association data",
                    m=row['mac'], log_tag=row['name'], m1=mac[0], n1=row['prev_name'], m2=row['prev_mac'], n2=name[0])
                log2.warn("Label {label} has no associated photometer now!", label=row['prev_name'])
            


    def updateCalibration(self, row):
        '''Updates Instrument calibration constant keeping its history'''
        def _updateCalibration(cursor, row):
            '''
            Updates Instrument calibration constant keeping its history
            row is a dictionary with at least the following keys: 'name', 'mac', 'calib'
            Returns a Deferred.
            '''
            cursor.execute(
                '''
                UPDATE tess_t SET valid_until = :eff_date, valid_state = :valid_expired
                WHERE mac_address == :mac AND valid_state == :valid_current
                ''', row)
            cursor.execute(
                '''
                INSERT INTO tess_t (
                    mac_address, 
                    zero_point,
                    valid_since,
                    valid_until,
                    valid_state,
                    authorised,
                    registered,
                    location_id
                ) VALUES (
                    :mac,
                    :calib,
                    :eff_date,
                    :exp_date,
                    :valid_current,
                    :authorised,
                    :registered,
                    :location
                )
                ''',  row)
        return self.pool.runInteraction( _updateCalibration, row )


# -------------------------------
# New refactored STUFF goes here
# -------------------------------

    @inlineCallbacks
    def maybeUpdateManagedAttributes(self, row):
        photometer = yield self.findPhotometerByName(row)
        photometer = photometer[0]
        log2.debug("{log_tag}: previous stored info is {photometer}",log_tag=row['name'], photometer=photometer)
        if row['calib'] != photometer[2]:
            row['location']   = photometer[3] # carries over the location id
            row['authorised'] = photometer[5] # carries over the authorised flag
            row['registered'] = photometer[6] # carries over the registration method
            yield self.updateCalibration(row)
            self.nZPChange += 1
            log2.info("{log_tag} changed instrument calibration data to {calib} (MAC = {mac})", log_tag=row['name'], calib=row['calib'], mac=row['mac'])
        else:
            self.nReboot += 1
            log2.info("Detected reboot for photometer {log_tag} (MAC = {mac})", log_tag=row['name'], mac=row['mac'])

    def lookupMAC(self, row):
        '''
        Look up instrument parameters given its MAC address
        row is a dictionary with at least the following keys: 'mac'
        Returns a Deferred.
        '''
        return self.pool.runQuery(
            '''
            SELECT mac_address, name
            FROM name_to_mac_t 
            WHERE mac_address == :mac
            AND  valid_state == :valid_current 
            ''', row)

    def lookupName(self, row):
        '''
        Look up association table looking by name
        row is a dictionary with at least the following keys: 'name'
        Returns a Deferred.
        '''
        return self.pool.runQuery(
            '''
            SELECT name, mac_address
            FROM name_to_mac_t 
            WHERE name == :name
            AND valid_state == :valid_current 
            ''', row)

    def findPhotometerByName(self, row):
        '''
        Give the current TESS photometer data associated to a name.
        Caches result if possible
        Returns a Deferred.
        '''
        if row['name'] in self._cache.keys():
            return defer.succeed(self._cache.get(row['name']))

        row['valid_current'] = CURRENT # needed when called by tess_readings.
        d = self.pool.runQuery(
            '''
            SELECT i.tess_id, i.mac_address, i.zero_point, i.location_id, i.filter, i.authorised, i.registered 
            FROM tess_t        AS i
            JOIN name_to_mac_t AS m USING (mac_address)
            WHERE m.name        == :name
            AND   m.valid_state == :valid_current
            AND   i.valid_state == :valid_current
            ''', row)

        d.addCallback(self.updateCache, row['name'])
        return d

    def addBrandNewTess(self, row):
        '''
        Adds a brand new instrument given its registration parameters.
        row is a dictionary with the following keys: 'name', 'mac', 'calib'
        Returns a Deferred.
        '''
        def _addBrandNewTess(cursor, row):
            # Create a new entry the photometer table
            cursor.execute(
                '''
               INSERT INTO tess_t (
                    mac_address,
                    registered,
                    zero_point,
                    valid_since,
                    valid_until,
                    valid_state
                ) VALUES (
                    :mac,
                    :registered,
                    :calib,
                    :eff_date,
                    :exp_date,
                    :valid_current
                )
             ''', row)
            # Create a new entry the name to MAC association table
            cursor.execute(
                '''
                INSERT INTO name_to_mac_t (
                    name,
                    mac_address,
                    valid_since,
                    valid_until,
                    valid_state
                ) VALUES (
                    :name,
                    :mac,
                    :eff_date,
                    :exp_date,
                    :valid_current
                )
            ''', row)
        return self.pool.runInteraction( _addBrandNewTess, row)


    def newTessReplacingBroken(self, row):
        '''
        Adds a brand new photometer with a given MAC
        but replaces the association table
        row is a dictionary with the following keys: 'name', 'mac', 'calib'
        Returns a Deferred.
        '''
        def _newTessReplacingBroken(cursor, row):
            # Expire current association with an existing name with new MAC
            cursor.execute(
                '''
                UPDATE name_to_mac_t 
                SET valid_until = :eff_date, valid_state = :valid_expired
                WHERE name == :name AND valid_state == :valid_current
            ''', row)
            # Create a new entry the name to MAC association table
            cursor.execute(
                '''
                INSERT INTO name_to_mac_t (
                    name,
                    mac_address,
                    valid_since,
                    valid_until,
                    valid_state
                ) VALUES (
                    :name,
                    :mac,
                    :eff_date,
                    :exp_date,
                    :valid_current
                )
            ''', row)
            # Create a new entry the photometer table
            cursor.execute(
                '''
               INSERT INTO tess_t (
                    mac_address,
                    registered,
                    zero_point,
                    valid_since,
                    valid_until,
                    valid_state
                ) VALUES (
                    :mac,
                    :registered,
                    :calib,
                    :eff_date,
                    :exp_date,
                    :valid_current
                )
             ''', row)
        return self.pool.runInteraction( _newTessReplacingBroken, row)


    def renamingAssociation(self, row):
        '''
        Adds a brand new photometer with a given MAC
        but replaces the association table
        row is a dictionary with the following keys: 'name', 'mac', 'calib'
        Returns a Deferred.
        '''
        def _renamingAssociation(cursor, row):
             # Expire current association with an existing name with new MAC
            cursor.execute(
                '''
                UPDATE name_to_mac_t 
                SET valid_until = :eff_date, valid_state = :valid_expired
                WHERE mac_address == :mac AND valid_state == :valid_current
                ''', row)
            # Insert a new association
            cursor.execute(
                '''
                INSERT INTO name_to_mac_t (
                    name,
                    mac_address,
                    valid_since,
                    valid_until,
                    valid_state
                ) VALUES (
                    :name,
                    :mac,
                    :eff_date,
                    :exp_date,
                    :valid_current
                )
            ''', row)
        return self.pool.runInteraction( _renamingAssociation, row)


    

    def overrideAssociations(self, row):
        def _overrideAssociations(cursor, row):
            '''
            Overrides two (name, MAC) associations in such a way that there is one name
            without a photometer.
            Returns a Deferred.
            '''
            cursor.execute(
                '''
                UPDATE name_to_mac_t SET valid_until = :eff_date, valid_state = :valid_expired
                WHERE mac_address == :prev_mac AND valid_state == :valid_current
                ''', row)
            # This association row leaves a name without a photometer.
            cursor.execute(
                '''
                UPDATE name_to_mac_t SET valid_until = :eff_date, valid_state = :valid_expired
                WHERE name == :prev_name AND valid_state == :valid_current
                ''', row)
            cursor.execute(
                '''
                INSERT INTO name_to_mac_t (
                    name,
                    mac_address,
                    valid_since,
                    valid_until,
                    valid_state
                ) VALUES (
                    :name,
                    :mac,
                    :eff_date,
                    :exp_date,
                    :valid_current
                );
                ''',  row)
        return self.pool.runInteraction( _overrideAssociations, row)

    