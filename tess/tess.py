# -*- coding: utf-8 -*-

# TESS UTILITY TO PERFORM SOME MAINTENANCE COMMANDS

# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys
import argparse
import sqlite3
import os
import os.path
import json
import datetime
import shlex
import subprocess

#--------------
# other imports
# -------------

from . import __version__

import tabulate
from tessdb.sqlite3.utils import CURRENT, UNKNOWN, NEVER_UP, ALWAYS_UP

# ----------------
# Module constants
# ----------------


DEFAULT_DBASE = "/var/dbase/tess.db"


INFINITE_TIME = "2999-12-31T23:59:59"
EXPIRED       = "Expired"
CURRENT       = "Current"
TSTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

UNKNOWN_SITE   = "Unknown"
OUT_OF_SERVICE = "Out of Service"

MANUAL = "Manual"

# Default values for version-controlled attributes

DEFAULT_AZIMUTH = 0.0   # Degrees, 0.0 = North
DEFAULT_ALTITUDE = 90.0 # Degrees, 90.0 = Zenith


# -----------------------
# Module global variables
# -----------------------

# -----------------------
# Module global functions
# -----------------------

def utf8(s):
    return unicode(s, 'utf8')

def createParser():
    # create the top-level parser
    parser = argparse.ArgumentParser(prog=sys.argv[0], description="tessdb command line utility " + __version__)

    subparser = parser.add_subparsers(dest='command')

    # --------------------------
    # Create first level parsers
    # --------------------------
    parser_instrument = subparser.add_parser('instrument', help='instrument commands')
    parser_location   = subparser.add_parser('location', help='location commands')
    parser_readings   = subparser.add_parser('readings', help='readings commands')
    parser_system     = subparser.add_parser('system', help='system related commands')

    # ------------------------------------------
    # Create second level parsers for 'location'
    # ------------------------------------------
    # Choices:
    #   tess location list
    #
    subparser = parser_location.add_subparsers(dest='subcommand')
    llp = subparser.add_parser('list', help='list locations')
    llp.add_argument('-n', '--name',      type=utf8,  help='specific location name')
    llp.add_argument('-p', '--page-size', type=int, default=10, help='list page size')
    llp.add_argument('-x', '--extended', action='store_true',  help='extended listing')
    llp.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    lkp = subparser.add_parser('unassigned', help='list unassigned locations')
    lkp.add_argument('-p', '--page-size', type=int, default=10, help='list page size')
    lkp.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')


    lcp = subparser.add_parser('create', help='create location')
    lcp.add_argument('site', metavar='<site>', type=utf8, help='Unique site name')
    lcp.add_argument('-o', '--longitude', type=float, default=0.0,       help='geographical longitude (degrees)')
    lcp.add_argument('-a', '--latitude',  type=float, default=0.0,       help='geographical latitude (degrees)')
    lcp.add_argument('-e', '--elevation', type=float, default=0.0,       help='elevation above sea level(meters)')
    lcp.add_argument('-z', '--zipcode',   type=utf8,  default='Unknown', help='Postal Code')
    lcp.add_argument('-l', '--location',  type=utf8,  default='Unknown', help='Location (village, town, city)')
    lcp.add_argument('-p', '--province',  type=utf8,  default='Unknown', help='Province')
    lcp.add_argument('-c', '--country',   type=utf8,  default='Unknown', help='Country')
    lcp.add_argument('-w', '--owner',     type=utf8,  default='Unknown', help='Contact person')
    lcp.add_argument('-m', '--email',     type=str,   default='Unknown', help='Contact email')
    lcp.add_argument('-g', '--org',       type=utf8,  default='Unknown', help='Organization')
    lcp.add_argument('-t', '--tzone',     type=str,   default='Etc/UTC', help='Olson Timezone')
    lcp.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    lup = subparser.add_parser('update', help='update location')
    lup.add_argument('site', metavar='<site>', type=utf8, help='Unique site name')
    lup.add_argument('-o', '--longitude', type=float, help='geographical longitude (degrees)')
    lup.add_argument('-a', '--latitude',  type=float, help='geographical latitude (degrees)')
    lup.add_argument('-e', '--elevation', type=float, help='elevation above sea level(meters)')
    lup.add_argument('-z', '--zipcode',   type=utf8,  help='Postal Code')
    lup.add_argument('-l', '--location',  type=utf8,  help='Location (village, town, city)')
    lup.add_argument('-p', '--province',  type=utf8,  help='Province')
    lup.add_argument('-c', '--country',   type=utf8,  help='Country')
    lup.add_argument('-w', '--owner',     type=utf8,  help='Contact person')
    lup.add_argument('-m', '--email',     type=str,   help='Contact email')
    lup.add_argument('-g', '--org',       type=utf8,  help='Organization')
    lup.add_argument('-t', '--tzone',     type=str,   help='Olson Timezone')
    lup.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    lre = subparser.add_parser('rename', help='rename location')
    lre.add_argument('old_site',  type=utf8, help='old site name')
    lre.add_argument('new_site',  type=utf8, help='new site name')
    lre.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    # ------------------------------------------
    # Create second level parsers for 'readings'
    # ------------------------------------------
    # Choices:
    #   tess location list
    #
    subparser = parser_readings.add_subparsers(dest='subcommand')
    rp = subparser.add_parser('list', help='list readings')
    rp.add_argument('-c', '--count', type=int, default=10, help='list up to <count> entries')
    rp.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    # --------------------------------------------
    # Create second level parsers for 'instrument'
    # --------------------------------------------
    # Choices:
    #   tess instrument list --name <instrument name>
    #   tess instrument assign <instrument name> <location name>
    #   tess instrument create <friendly name> <MAC address> <Calibration Constant>
    #   tess instrument rename <old friendly name> <new friendly name>
    #   tess instrument update <friendly name> --zero-point <new zero point> --filter <new filter> --latest
    #   tess instrument delete <instrument name> 
    #   tess instrument enable <instrument name> 
    #   tess instrument disable <instrument name> 
    #
    subparser = parser_instrument.add_subparsers(dest='subcommand')
    parser_instrument_assign = subparser.add_parser('assign', help='assign instrument to location')
    parser_instrument_assign.add_argument('instrument', metavar='<instrument>', type=str, help='TESS instrument name')
    parser_instrument_assign.add_argument('location',   metavar='<location>',   type=utf8,  help='Location name')
    parser_instrument_assign.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    ip = subparser.add_parser('list', help='list instruments')
    ip.add_argument('-n', '--name', type=str, help='specific instrument name')
    ip.add_argument('-p', '--page-size', type=int, default=10, help='list page size')
    ip.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')
    ip.add_argument('-l', '--log', action='store_true', default=False, help='show TESS instrument change log')

    ik = subparser.add_parser('unassigned', help='list unassigned instruments')
    ik.add_argument('-p', '--page-size', type=int, default=10, help='list page size')
    ik.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    iaz = subparser.add_parser('enable', help='enable storing instrument samples')
    iaz.add_argument('name',  metavar='<instrument>', type=str,   help='instrument friendly name')
    iaz.add_argument('-p', '--page-size', type=int, default=10, help='list page size')
    iaz.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    iuz = subparser.add_parser('disable', help='disable storing samples for instrument')
    iuz.add_argument('name',  metavar='<instrument>', type=str,   help='instrument friendly name')
    iuz.add_argument('-p', '--page-size', type=int, default=10, help='list page size')
    iuz.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    ihi = subparser.add_parser('history',  help='single instrument history')
    ihi.add_argument('name',   type=str,   help='friendly name')
    ihi.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    icr = subparser.add_parser('create',   help='create instrument')
    icr.add_argument('name',   type=str,   help='friendly name')
    icr.add_argument('mac',    type=str,   help='MAC address')
    icr.add_argument('zp',     type=float, help='Zero Point')
    icr.add_argument('filter', type=str,   help='Filter (i.e. DG, BG39, GG495, etc.)')
    icr.add_argument('-a', '--azimuth',    type=float, default=DEFAULT_AZIMUTH, help='Azimuth (degrees). 0.0 = North')
    icr.add_argument('-t', '--altitude',   type=float, default=DEFAULT_ALTITUDE, help='Altitude (degrees). 90.0 = Zenith')
    icr.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    ire = subparser.add_parser('rename', help='rename instrument')
    ire.add_argument('old_name',  type=str, help='old friendly name')
    ire.add_argument('new_name',  type=str, help='new friendly name')
    ire.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    ide = subparser.add_parser('delete', help='delete instrument')
    ide.add_argument('name',  type=str, help='instrument friendly name')
    ide.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')

    iup = subparser.add_parser('update',   help='update instrument attributes')
    iup.add_argument('name',   type=str,   help='instrument friendly name')
    iup.add_argument('-z', '--zero-point', type=float, help='new zero point')
    iup.add_argument('-f', '--filter',     type=str,  help='new filter glass')
    iup.add_argument('-a', '--azimuth',    type=float, help='Azimuth (degrees). 0.0 = North')
    iup.add_argument('-t', '--altitude',   type=float, help='Altitude (degrees). 90.0 = Zenith')
    iup.add_argument('-r', '--registered', type=str, choices=["Manual","Automatic","Unknown"], help='Registration Method: [Unknown,Manual,Automatic]')
    iup.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')
    iupex = iup.add_mutually_exclusive_group()
    now = datetime.datetime.utcnow().strftime(TSTAMP_FORMAT)
    iupex.add_argument("-s", "--start-time", type=str, default=now, metavar="YYYYMMDDTHHMMSS", help='update start date')
    iupex.add_argument('-l', '--latest', action='store_true', default=False, help='Latest entry only (no change control)')
    
    # ------------------------------------------
    # Create second level parsers for 'system'
    # ------------------------------------------
    # Choices:
    #   tess system window
    #
    subparser = parser_system.add_subparsers(dest='subcommand')
    syw = subparser.add_parser('window', help='show current system maintenance window')
    syw.add_argument('-d', '--dbase', default=DEFAULT_DBASE, help='SQLite database full file path')
    syw.add_argument('-r', '--restart', action='store_true', default=False, help='Schedule "at job" to restart tessdb')
 
    return parser

def main():
    '''
    Utility entry point
    '''
    try:
        invalid_cache = False
        options = createParser().parse_args(sys.argv[1:])
        connection = open_database(options)
        command = options.command
        subcommand = options.subcommand
        if subcommand in ["rename","enable","disable","update","delete"]:
            invalid_cache = True
        # Call the function dynamically
        func = command + '_' + subcommand
        globals()[func](connection, options)

    except KeyboardInterrupt:
        print('')
    except Exception as e:
        print("Error => {0}".format( utf8(str(e)) ))
    finally:
        if invalid_cache:
            print("WARNING: Do not forget to issue 'service tessdb reload' afterwards to invalidate tessdb caches")

# ==============
# DATABASE STUFF
# ==============

def open_database(options):
    if not os.path.exists(options.dbase):
        raise IOError("No SQLite3 Database file found in {0}. Exiting ...".format(options.dbase))
    return sqlite3.connect(options.dbase)
 

def paging(cursor, headers, size=10):
    '''
    Pages query output and displays in tabular format
    '''
    ONE_PAGE = 10
    while True:
        result = cursor.fetchmany(ONE_PAGE)
        print tabulate.tabulate(result, headers=headers, tablefmt='grid')
        if len(result) < ONE_PAGE:
            break
        size -= ONE_PAGE
        if size > 0:
            raw_input("Press Enter to continue [Ctrl-C to abort] ...")
        else:
            break

# ----------------------
# INSTRUMENT SUBCOMMANDS
# ----------------------

def instrument_assign(connection, options):
    cursor = connection.cursor()
    row = {'site': options.location, 'tess': options.instrument, 'state': CURRENT}
    cursor.execute("SELECT location_id FROM location_t WHERE site == :site",row)
    res =  cursor.fetchone()
    if not res:
        print("Location not found by {0}".format(row['site']))
        sys.exit(1)
    row['ident'] = res[0]
    cursor.execute(
        '''
        UPDATE tess_t SET location_id = :ident
        WHERE name == :tess
        ''', row)
    cursor.execute(
        '''
        SELECT name,site
        FROM tess_v
        WHERE valid_state == :state
        AND name = :tess
        ''',row)
    paging(cursor,["TESS","Site"])
    connection.commit()    


def instrument_single_history(connection, options):
    cursor = connection.cursor()
    row = {'tess': options.name }
    cursor.execute(
            '''
            SELECT name,tess_id,mac_address,zero_point,filter,azimuth,altitude,valid_since,valid_until
            FROM tess_t
            WHERE name = :tess
            ORDER BY tess_t.valid_since ASC;
            ''',row)
    paging(cursor,["TESS","Id","MAC Addr.","Zero Point","Filter","Azimuth","Altitude","Since","Until"], size=100)


def instrument_list(connection, options):
    if options.name is None:
        if options.log:
            instrument_historic_list(connection, options)
        else:
            instrument_current_list(connection, options)
    else:
        if options.log:
            instrument_specific_historic_list(connection, options)
        else:
            instrument_specific_current_list(connection, options)

def instrument_historic_list(connection, options):
    cursor = connection.cursor()
    cursor.execute(
            '''
            SELECT name,mac_address,zero_point,filter,site,valid_since,valid_until,authorised,registered
            FROM tess_v
            ORDER BY CAST(substr(tess_v.name, 6) as decimal) ASC, tess_v.valid_since ASC;
            ''')
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Site","Since","Until","Enabled","Registered"], size=100)


def instrument_specific_historic_list(connection, options):
    cursor = connection.cursor()
    row = {'state': CURRENT, 'name': options.name}
    cursor.execute(
            '''
            SELECT name,mac_address,zero_point,filter,site,valid_since,valid_until,authorised,registered
            FROM tess_v
            WHERE name == :name
            ORDER BY tess_v.valid_since ASC;
            ''',row)
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Site","Since","Until","Enabled","Registered"], size=100)


def instrument_current_list(connection, options):
    cursor = connection.cursor()
    row = {'state': CURRENT}
    cursor.execute(
            '''
            SELECT name,mac_address,zero_point,filter,site,authorised,registered
            FROM tess_v
            WHERE valid_state == :state
            ORDER BY CAST(substr(tess_v.name, 6) as decimal) ASC;
            ''', row)
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Site","Enabled","Registered"], size=100)


def instrument_specific_current_list(connection, options):
    cursor = connection.cursor()
    row = {'state': CURRENT, 'name': options.name}
    cursor.execute(
            '''
            SELECT name,mac_address,zero_point,filter,site,authorised,registered
            FROM tess_v
            WHERE valid_state == :state
            AND name == :name;
            ''', row)
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Site","Enabled","Registered"], size=100)


def instrument_unassigned(connection, options):
    cursor = connection.cursor()
    row = {'state': CURRENT, 'site1': UNKNOWN_SITE, 'site2': OUT_OF_SERVICE}
    cursor.execute(
            '''
            SELECT name,mac_address,zero_point,filter,azimuth,altitude,site,authorised,registered
            FROM tess_v
            WHERE valid_state == :state
            AND (site == :site1 OR site == :site2)
            ORDER BY CAST(substr(tess_v.name, 6) as decimal) ASC;
            ''', row)
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Azimuth","Altitude","Site","Enabled","Registered"], size=100)


def instrument_enable(connection, options):
    cursor = connection.cursor()
    row = {'tess': options.name, 'state': CURRENT}
    cursor.execute('''
        UPDATE tess_t 
        SET authorised = 1 
        WHERE name == :tess 
        AND valid_state == :state
        ''',row)
    
    cursor.execute(
        '''
        SELECT name,site,authorised
        FROM tess_v
        WHERE valid_state == :state
        AND name = :tess
        ''',row)
    paging(cursor,["TESS","Site","Authorised"])
    connection.commit()    

def instrument_disable(connection, options):
    cursor = connection.cursor()
    row = {'tess': options.name, 'state': CURRENT}
    cursor.execute('''
        UPDATE tess_t 
        SET authorised = 0 
        WHERE name == :tess 
        AND valid_state == :state
        ''',row)
    
    cursor.execute(
        '''
        SELECT name,site,authorised
        FROM tess_v
        WHERE valid_state == :state
        AND name = :tess
        ''',row)
    paging(cursor,["TESS","Site","Authorised"])
    connection.commit()    


def instrument_create(connection, options):
    cursor = connection.cursor()
    row = {}
    row['name']       = options.name
    row['mac']        = options.mac
    row['zp']         = options.zp
    row['filter']     = options.filter
    row['azimuth']    = options.azimuth
    row['altitude']   = options.altitude
    row['valid_flag'] = CURRENT
    row['eff_date']   = datetime.datetime.utcnow().strftime(TSTAMP_FORMAT)
    row['exp_date']   = INFINITE_TIME
    row['registered'] = MANUAL;
    
    # Find existing MAC and abort if so
    cursor.execute(
        '''
        SELECT name, mac_address
        FROM tess_t 
        WHERE mac_address == :mac
        AND valid_state == :valid_flag
        ''', row)
    result = cursor.fetchone()
    if result:
        raise IndexError("Already existing MAC %s" % (row['mac'],) )
    # Find existing name and abort if so
    cursor.execute(
        '''
        SELECT name, mac_address
        FROM tess_t 
        WHERE name == :name
        AND valid_state == :valid_flag 
        ''', row)
    result = cursor.fetchone()
    if result:
        raise IndexError("Other instrument already using friendly name %s" (row['name'],) )
    # Write into database
    cursor.execute(
        '''
        INSERT INTO tess_t (
            name,
            mac_address, 
            zero_point,
            filter,
            azimuth,
            altitude,
            registered,
            valid_since,
            valid_until,
            valid_state
        ) VALUES (
            :name,
            :mac,
            :zp,
            :filter,
            :azimuth,
            :altitude,
            :registered,
            :eff_date,
            :exp_date,
            :valid_flag
        )
        ''',  row)
    connection.commit()
    # Now display it
    cursor.execute(
        '''
        SELECT name, mac_address, zero_point, filter, azimuth, altitude, registered, site
        FROM   tess_v
        WHERE  name == :name
        AND    valid_state == :valid_flag
        ''', row)
    paging(cursor,["TESS","MAC Addr.","Calibration","Filter","Azimuth","Altitude","Registered","Site"])



def instrument_rename(connection, options):
    cursor = connection.cursor()
    row = {}
    row['newname']  = options.new_name
    row['oldname']  = options.old_name
    cursor.execute("SELECT mac_address FROM tess_t WHERE name == :oldname", row)
    result = cursor.fetchone()
    if not result:
        raise IndexError("Cannot rename. Existing instrument with old name %s does not exist." 
            % (options.old_name,) )
    cursor.execute("SELECT mac_address FROM tess_t WHERE name == :newname", row)
    result = cursor.fetchone()
    if result:
        raise IndexError("Cannot rename. Existing instrument MAC %s owns this name." % (result[0],) ) 
    cursor.execute("UPDATE tess_t SET name = :newname WHERE name == :oldname", row)
    connection.commit()
    # Now display it
    row['valid_flag'] = CURRENT
    cursor.execute(
        '''
        SELECT name,mac_address,zero_point,filter,azimuth,altitude,site
        FROM   tess_v
        WHERE  name == :newname
        AND    valid_state == :valid_flag
        ''', row)
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Azimuth","Altitude","Site"])


def instrument_delete(connection, options):
    cursor = connection.cursor()
    row = {}
    row['name']  = options.name

    cursor.execute("SELECT mac_address FROM tess_t WHERE name == :name", row)
    result = cursor.fetchone()
    if not result:
        raise IndexError("Cannot delete. Instrument with name %s does not exist." 
            % (options.name,) )
    
    # Find out what's being deleted
    print("About to delete")
    cursor.execute(
        '''
        SELECT name,mac_address,zero_point,filter,azimuth,altitude,site
        FROM   tess_v
        WHERE  name == :name
        ''', row)
    paging(cursor,["TESS","MAC Addr.","Zero Point","Filter","Azimuth","Altitude","Site"])
    
    # Find out if it has accumulated readings
    # This may go away if readings are stored in another database (i.e influxdb)
    cursor.execute(
        '''
        SELECT i.name, count(*) AS readings
        FROM tess_readings_t AS r
        JOIN tess_t          AS i USING (tess_id)
        WHERE i.name == :name
        ''', row)
    paging(cursor,["TESS","Acumulated Readings"])
    raw_input("Are you sure ???? Press Enter to continue [Ctrl-C to abort] ...")

    cursor.execute("DELETE FROM tess_t WHERE name == :name", row)
    connection.commit()
    print("Instrument deleted")


def instrument_update(connection, options):
    if options.latest:
        instrument_raw_update(connection, options)
    else:
        try:
            datetime.datetime.strptime(options.start_time, TSTAMP_FORMAT)
        except ValueError as e:
            print("Invalid start date YYYY-MM-DDTHH:MM:SS format: => %s" % (options.start_time,) )
        else:
            instrument_controlled_update(connection, options)


def instrument_raw_update(connection, options):
    '''Raw update lastest instrument calibration constant (with 'Current' state)'''
    cursor = connection.cursor()
    row = {}
    row['name']       = options.name
    row['valid_flag'] = CURRENT
    cursor.execute(
        '''
        SELECT name, mac_address, location_id
        FROM tess_t 
        WHERE name == :name
        AND valid_state == :valid_flag 
        ''', row)
    result = cursor.fetchone()
    if not result:
        raise IndexError("Cannot rename. Existing instrument with name %s does not exist."
         % (options.name,) )
    row['mac']           = result[1]

    # Change only if passed in the command line
    if options.zero_point is not None:
        row['zp'] = options.zero_point
        cursor.execute(
        '''
        UPDATE tess_t SET zero_point = :zp
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)

    if options.filter is not None:
        row['filter'] = options.filter
        cursor.execute(
        '''
        UPDATE tess_t SET filter = :filter
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)

    if options.azimuth is not None:
        row['azimuth'] = options.azimuth
        cursor.execute(
        '''
        UPDATE tess_t SET azimuth = :azimuth
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)

    if options.altitude is not None:
        row['altitude'] = options.altitude
        cursor.execute(
        '''
        UPDATE tess_t SET altitude = :altitude
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)

    if options.registered is not None:
        row['registered'] = options.registered
        cursor.execute(
        '''
        UPDATE tess_t SET registered = :registered
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)

    connection.commit()
    print("Operation complete.")
    cursor.execute(
        '''
        SELECT name, zero_point, filter, azimuth, altitude, valid_state, valid_since, valid_until, registered, site
        FROM   tess_v
        WHERE  name == :name AND valid_state == :valid_flag 
        ''', row)
    paging(cursor,["TESS","Zero Point","Filter","Azimuth","Altitude","State","Since","Until", "Registered", "Site"])




def instrument_controlled_update(connection, options):
    '''
    Update lastest instrument calibration constant with control change
    creating a new row with new calibration state and valid interval
    '''
    cursor = connection.cursor()
    row = {}
    row['name']       = options.name
    row['valid_flag'] = CURRENT
    cursor.execute(
        '''
        SELECT name, mac_address, location_id, valid_since, zero_point, filter, azimuth, altitude, authorised, registered 
        FROM tess_t 
        WHERE name == :name
        AND valid_state == :valid_flag 
        ''', row)
    result = cursor.fetchone()
    if not result:
        raise IndexError("Cannot rename. Existing instrument with name %s does not exist." % (options.name,) )
    if result[3] >= options.start_time:
        raise ValueError("Cannot set valid_since (%s) column to an equal or earlier date (%s)" % (result[3], options.start_time) )

    row['mac']           = result[1]
    row['location']      = result[2]
    row['eff_date']      = options.start_time
    row['exp_date']      = INFINITE_TIME
    row['valid_expired'] = EXPIRED
    row['zp']            = result[4] if options.zero_point is None else options.zero_point
    row['filter']        = result[5] if options.filter is None else options.filter
    row['azimuth']       = result[6] if options.azimuth is None else options.azimuth
    row['altitude']      = result[7] if options.altitude is None else options.altitude
    row['authorised']    = result[8]
    row['registered']    = result[9] if options.registered is None else options.registered
    cursor.execute(
        '''
        UPDATE tess_t SET valid_until = :eff_date, valid_state = :valid_expired
        WHERE mac_address == :mac AND valid_state == :valid_flag
        ''', row)

    cursor.execute(
        '''
        INSERT INTO tess_t (
            name,
            mac_address, 
            zero_point,
            filter,
            azimuth,
            altitude,
            valid_since,
            valid_until,
            valid_state,
            authorised,
            registered,
            location_id
        ) VALUES (
            :name,
            :mac,
            :zp,
            :filter,
            :azimuth,
            :altitude,
            :eff_date,
            :exp_date,
            :valid_flag,
            :authorised,
            :registered,
            :location
            )
        ''',  row)
    connection.commit()
    print("Operation complete.")
    
    cursor.execute(
        '''
        SELECT name, zero_point, filter, azimuth, altitude, valid_state, valid_since, valid_until, authorised, registered, site
        FROM   tess_v
        WHERE  name == :name
        ''', row)
    paging(cursor,["TESS","Zero Point","Filter","Azimuth","Altitude","State","Since","Until", "Authorised","Registered","Site"])


# --------------------
# LOCATION SUBCOMMANDS
# --------------------

def location_list_short(connection, options):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email 
        FROM location_t 
        WHERE location_id > -1 
        ORDER BY location_id ASC
        ''')
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email"], size=100)

def location_list_long(connection, options):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email,organization,zipcode,location,province,country,timezone
        FROM location_t 
        WHERE location_id > -1 
        ORDER BY location_id ASC
        ''')
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email","Organization","ZIP Code","Location","Province","Country","Timezone"], size=100)


def location_single_list_short(connection, options):
    row = {}
    row['name']  = options.name
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email 
        FROM location_t 
        WHERE site = :name
        ''', row)
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email"], size=100)


def location_single_list_long(connection, options):
    row = {}
    row['name']  = options.name
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email,organization,zipcode,location,province,country,timezone
        FROM location_t 
        WHERE site = :name
        ''', row)
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email","Organization","ZIP Code","Location","Province","Country","Timezone"], size=100)


def location_list(connection, options):
    if options.name is not None:
        if options.extended:
            location_single_list_long(connection, options)
        else:
            location_single_list_short(connection, options)
    else:
        if options.extended:
            location_list_long(connection,options)
        else:
            location_list_short(connection,options)


def location_unassigned(connection, options):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT l.site,l.longitude,l.latitude,l.elevation,l.contact_name,l.contact_email 
        FROM location_t        AS l 
        LEFT OUTER JOIN tess_t AS i USING (location_id)
        WHERE i.name IS NULL;
        ''')
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email"], size=100)


# Location update is a nightmare if done properly, since we have to generate
# SQL updates tailored to the attributes being given in the command line

def location_create(connection, options):
    cursor = connection.cursor()
    row = {}
    row['site']      = options.site
    row['longitude'] = options.longitude
    row['latitude']  = options.latitude
    row['elevation'] = options.elevation
    row['zipcode']   = options.zipcode
    row['location']  = options.location
    row['province']  = options.province
    row['country']   = options.country
    row['email']     = options.email
    row['owner']     = options.owner
    row['org']       = options.org
    row['tzone']     = options.tzone
    # Fetch existing site
    cursor.execute(
        '''
        SELECT site 
        FROM   location_t 
        WHERE site == :site
        ''', row)
    result = cursor.fetchone()
    if result:
        raise IndexError("Cannot create. Existing site with name %s already exists." % (options.site,) )
    cursor.execute(
        '''
        INSERT INTO location_t (
            site,
            longitude, 
            latitude,
            elevation,
            zipcode,
            location,
            province,
            country,
            contact_email,
            contact_name,
            organization,
            timezone
        ) VALUES (
            :site,
            :longitude,
            :latitude,
            :elevation,
            :zipcode,
            :location,
            :province,
            :country,
            :email,
            :owner,
            :org,
            :tzone
            )
        ''',  row)
    connection.commit()
    # Read just written data
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email,organization,zipcode,location,province,country,timezone
        FROM location_t 
        WHERE site == :site
        ORDER BY location_id ASC
        ''', row)
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email","Organization","ZIP Code","Location","Province","Country","Timezone"], size=5)



def location_update(connection, options):
    cursor = connection.cursor()
    row = {} 
    row['site'] = options.site
   
    # Fetch existing site
    cursor.execute(
        '''
        SELECT site 
        FROM   location_t 
        WHERE site == :site
        ''', row)
    result = cursor.fetchone()
    if not result:
        raise IndexError("Cannot update. Site with name %s does not exists." % (options.site,) )
    
    if options.longitude is not None:
        row['longitude'] = options.longitude
        cursor.execute(
        '''
        UPDATE location_t SET longitude = :longitude WHERE site == :site
        ''', row)

    if options.latitude is not None:
        row['latitude']  = options.latitude
        cursor.execute(
        '''
        UPDATE location_t SET latitude = :latitude WHERE site == :site
        ''', row)
        
    if options.elevation is not None:
        row['elevation'] = options.elevation
        cursor.execute(
        '''
        UPDATE location_t SET elevation = :elevation WHERE site == :site
        ''', row)

    if options.zipcode is not None:
        row['zipcode']   = options.zipcode
        cursor.execute(
        '''
        UPDATE location_t SET zipcode = :zipcode WHERE site == :site
        ''', row)

    if options.location is not None:
        row['location']  = options.location
        cursor.execute(
        '''
        UPDATE location_t SET location = :location WHERE site == :site
        ''', row)

    if options.province is not None:
        row['province']  = options.province
        cursor.execute(
        '''
        UPDATE location_t SET province = :province WHERE site == :site
        ''', row)

    if options.country is not None:
        row['country']  = options.country
        cursor.execute(
        '''
        UPDATE location_t SET country = :country WHERE site == :site
        ''', row)

    if options.email is not None:
        row['email']   = options.email
        cursor.execute(
        '''
        UPDATE location_t SET contact_email = :email WHERE site == :site
        ''', row)

    if options.owner is not None:
        row['owner']   = options.owner
        cursor.execute(
        '''
        UPDATE location_t SET contact_name = :owner WHERE site == :site
        ''', row)

    if options.org is not None:
        row['org']   = options.org
        cursor.execute(
        '''
        UPDATE location_t SET organization = :org WHERE site == :site
        ''', row)

    if options.tzone is not None:
        row['tzone']   = options.tzone
        cursor.execute(
        '''
        UPDATE location_t SET timezone = :tzone WHERE site == :site
        ''', row)

    connection.commit()
    # Read just written data
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email,organization,zipcode,location,province,country,timezone
        FROM location_t 
        WHERE site == :site
        ORDER BY location_id ASC
        ''', row)
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email","Organization","ZIP Code","Location","Province","Country","Timezone"], size=5)


def location_rename(connection, options):
    cursor = connection.cursor()
    row = {}
    row['newsite']  = options.new_site
    row['oldsite']  = options.old_site
    cursor.execute("SELECT site FROM location_t WHERE site == :oldsite", row)
    result = cursor.fetchone()
    if not result:
        raise IndexError("Cannot rename. Existing site with old name %s does not exist." 
            % (options.old_site,) )
    
    cursor.execute("SELECT site FROM location_t WHERE site == :newsite", row)
    result = cursor.fetchone()
    if result:
        raise IndexError("Cannot rename. New site %s already exists." % (result[0],) ) 
    cursor.execute("UPDATE location_t SET site = :newsite WHERE site == :oldsite", row)
    connection.commit()
    # Now display it
    cursor.execute(
        '''
        SELECT site,longitude,latitude,elevation,contact_name,contact_email,organization,zipcode,location,province,country,timezone
        FROM location_t 
        WHERE site == :newsite
        ''', row)
    paging(cursor,["Name","Longitude","Latitude","Elevation","Contact","Email","Organization","ZIP Code","Location","Province","Country","Timezone"], size=5)

# --------------------
# READINGS SUBCOMMANDS
# --------------------

def readings_list(connection, options):
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT (d.sql_date || 'T' || t.time) AS timestamp, i.name, l.site, r.frequency, r.magnitude, r.signal_strength
        FROM tess_readings_t as r
        JOIN date_t     as d USING (date_id)
        JOIN time_t     as t USING (time_id)
        JOIN location_t as l USING (location_id)
        JOIN tess_t     as i USING (tess_id)
        ORDER BY r.date_id DESC, r.time_id DESC
        LIMIT %s
        ''' % options.count)
    paging(cursor, ["Timestamp (UTC)","TESS","Location","Frequency","Magnitude","RSS"], size=options.count)
   
 
# --------------------
# SYSTEM SUBCOMMANDS
# --------------------

def system_window(connection, options):
    ONE_PAGE = 10
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT DISTINCT l.sunrise,l.sunset,l.site, l.country, t.name
        FROM tess_t     AS t 
        JOIN location_t AS l USING (location_id)
        WHERE l.location_id > -1
        AND t.valid_state = "Current"
        ''')

    sunrise_list = []
    sunset_list  = []
    sites_dict   = {}
    while True:
        result = cursor.fetchone()
        if result is None:
            break
        try:
            info = result[4] + ', ' + result[2] + ' (' + result[3] +')'
            sunrise = datetime.datetime.strptime(result[0], "%Y/%m/%d %H:%M:%S")
            sunset  = datetime.datetime.strptime(result[1], "%Y/%m/%d %H:%M:%S")
        except Exception as e:
            if result[0] == NEVER_UP: print("FUNCIONALIDAD INACABADA ...")
        else:
            sites_dict[sunrise] = info
            sites_dict[sunset]  = info
            if sunrise > sunset:
                sunrise_list.append(sunrise)
                # Good approximation, since sunset will be slightly different
                sunset_list.append(sunset + datetime.timedelta(hours=24))  
            else:
                sunrise_list.append(sunrise)
                sunset_list.append(sunset)
    
    # Find out the Window State
    window_start = max(sunrise_list)
    window_end   = min(sunset_list)
    window_duration = window_end - window_start
    utcnow = datetime.datetime.utcnow()
    utcoffset = datetime.datetime.now() - utcnow     # The 'at' command uses local time
    window_open_flag = False
    if window_start >= window_end:
        window_state = "CLOSED FOR WINTER"
    elif window_start <  utcnow < window_end:
        window_state = "OPEN"
        window_open_flag = True
    elif utcnow <= window_start:
        window_state = "WAITING TO OPEN"
    else:
        window_state = "CLOSED FOR TODAY"
    table = [ [window_start, window_end, window_duration, window_state] ]
    print (tabulate.tabulate(table, headers=["Start Time (UTC)","End Time (UTC)","Window Size", "State"], tablefmt='grid'))
    print("Window start given by: %s" % sites_dict[window_start])
    print("Window end   given by: %s" % sites_dict[window_end])
    
    # Restart if requested
    if not options.restart:
        return

    if utcnow < window_start:
        exec_tstamp = (window_start + utcoffset + datetime.timedelta(minutes=1)).strftime("%H:%M")
    elif utcnow < window_end:
        exec_tstamp = (window_end + utcoffset - datetime.timedelta(minutes=1)).strftime("%H:%M")
    else:
        print("Cannot schedule an 'at job' for today: %s" % window_state)
        return
    cmd1 = shlex.split('echo "sudo service tessdb restart"')
    cmd2 = shlex.split("at %s" % exec_tstamp)
    p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    output = p2.communicate()[0]
    print(output)
       
