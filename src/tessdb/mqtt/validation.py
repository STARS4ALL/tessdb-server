# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import os
import errno
import sys
import datetime
import json
import math

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger, LogLevel
from twisted.internet import reactor, task
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet.endpoints import clientFromString
from twisted.internet.defer import inlineCallbacks

from mqtt import v311
from mqtt.error import MQTTStateError
from mqtt.client.factory import MQTTFactory

# --------------
# local imports
# -------------

from tessdb.error import ValidationError, ReadingKeyError, ReadingTypeError, RegistrationTypeError, RegistrationKeyError
from tessdb.mqtt import NAMESPACE, TESS4C_FILTER_KEYS

# ----------------
# Module constants
# ----------------

# Mandatory keys in each JSON register message
MANDATORY_REGR_TESSW = set(['name', 'mac', 'calib', 'rev'])
MANDATORY_REGR_TESS4C = set(['name', 'mac', 'rev', 'F1', 'F2', 'F3', 'F4'])

# Mandatory keys in each JSON reading message
MANDATORY_READ_TESSW = set(
    ['seq', 'name', 'freq', 'mag', 'tamb', 'tsky', 'rev'])
MANDATORY_READ_TESS4C = set(['seq', 'name', 'rev', 'F1', 'F2', 'F3', 'F4'])

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------
# Auxiliar functions
# ------------------


def _validateCommonReadingsOptionals(row):
    '''Common optionals fro TESS-W and TESS4C'''
    if 'az' in row and type(row['az']) != float:
        raise ReadingTypeError('az', float, type(row['az']))
    if 'alt' in row and type(row['alt']) != float:
        raise ReadingTypeError('alt', float, type(row['alt']))
    if 'long' in row and type(row['long']) != float:
        raise ReadingTypeError('long', float, type(row['long']))
    if 'lat' in row and type(row['lat']) != float:
        raise ReadingTypeError('lat', float, type(row['lat']))
    if 'height' in row and type(row['height']) != float:
        raise ReadingTypeError('height', float, type(row['height']))
    if 'wdBm' in row and type(row['wdBm']) != int:
        raise ReadingTypeError('wdBm', int, type(row['wdBm']))
    # new field value for readings consistency check
    if 'hash' in row and not (type(row['hash']) == str):
        raise ReadingTypeError('hash', str, type(row['hash']))


# ------------------
# Exported functions
# ------------------

def validateRegisterTESSW(row):
    '''validate the TESS-W registration fields'''
    # Test mandatory keys
    incoming = set(row.keys())
    if not MANDATORY_REGR_TESSW <= incoming:
        raise ReadingKeyError(MANDATORY_REGR_TESSW - incoming)
    # Mandatory field values
    if type(row['rev']) != int:
        raise ReadingTypeError('rev', int, type(row['rev']))
    if not(type(row['name']) == str):
        raise ReadingTypeError('name', str, type(row['name']))
    if not(type(row['mac']) == str):
        raise ReadingTypeError('mac', str, type(row['mac']))
    if type(row['calib']) != float:
        raise ReadingTypeError('calib', float, type(row['calib']))
    # optionals field values in Payload V1 format
    if 'firmware' in row and not (type(row['firmware']) == str):
        raise ReadingTypeError('firmware', str, type(row['firmware']))
    if 'model' in row and not (type(row['model']) == str):
        raise ReadingTypeError('model', str, type(row['model']))


def validateReadingsTESSW(row):
    '''validate TESS-W readings fields'''
    # Test mandatory keys
    incoming = set(row.keys())
    if not MANDATORY_READ_TESSW <= incoming:
        raise ReadingKeyError(MANDATORY_READ_TESSW - incoming)
    # Mandatory field values
    if type(row['freq']) != float:
        raise ReadingTypeError('freq', float, type(row['freq']))
    if type(row['mag']) != float:
        raise ReadingTypeError('mag', float, type(row['mag']))
    if not(type(row['name']) == str):
        raise ReadingTypeError('name', str, type(row['name']))
    if type(row['seq']) != int:
        raise ReadingTypeError('seq', int, type(row['seq']))
    if type(row['tamb']) != float:
        raise ReadingTypeError('tamb', float, type(row['tamb']))
    if type(row['tsky']) != float:
        raise ReadingTypeError('tsky', float, type(row['tsky']))
    if type(row['rev']) != int:
        raise ReadingTypeError('rev', int, type(row['rev']))
    _validateCommonReadingsOptionals(row)


def validateRegisterTESS4C(row):
    '''validate the TESS4C registration fields'''
    # Test mandatory keys
    incoming = set(row.keys())
    if not MANDATORY_REGR_TESS4C <= incoming:
        raise RegistrationKeyError(MANDATORY_REGR_TESS4C - incoming)
    # Mandatory field values
    if type(row['rev']) != int:
        raise RegistrationTypeError('rev', int, type(row['rev']))
    if not(type(row['name']) == str):
        raise RegistrationTypeError('name', str, type(row['name']))
    if not(type(row['mac']) == str):
        raise RegistrationTypeError('mac', str, type(row['mac']))
    # optionals field values
    if 'firmware' in row and not (type(row['firmware']) == str):
        raise RegistrationTypeError('firmware', str, type(row['firmware']))
    mandatory = set(['band', 'calib'])
    for filt in TESS4C_FILTER_KEYS:
        incoming = set(row[filt].keys())
        if not mandatory <= incoming:
            raise RegistrationKeyError(mandatory - incoming)
        item = row[filt]
        if type(item['band']) != str:
            raise RegistrationTypeError('band', str, type(item['band']))
        if type(item['calib']) != float:
            raise RegistrationTypeError('calib', float, type(item['float']))


def validateReadingsTESS4C(row):
    '''validate the TESS4C readings fields'''
    # Test mandatory keys
    incoming = set(row.keys())
    if not MANDATORY_READ_TESS4C <= incoming:
        log.info("CUCU")
        raise ReadingKeyError(MANDATORY_READ_TESS4C - incoming)
    if not(type(row['name']) == str):
        raise ReadingTypeError('name', str, type(row['name']))
    if type(row['seq']) != int:
        raise ReadingTypeError('seq', int, type(row['seq']))
    if type(row['rev']) != int:
        raise ReadingTypeError('rev', int, type(row['rev']))
    mandatory = set(['freq', 'mag', 'zp'])
    for filt in TESS4C_FILTER_KEYS:
        incoming = set(row[filt].keys())
        if not mandatory <= incoming:
            log.info("TRAS")
            raise ReadingKeyError(mandatory - incoming)
        item = row[filt]
        if type(item['freq']) != float:
            raise ReadingTypeError('freq', float, type(item['freq']))
        if type(item['mag']) != float:
            raise ReadingTypeError('mag', float, type(item['mag']))
        if type(item['zp']) != float:
            raise ReadingTypeError('zp', float, type(item['zp']))
    if 'tsky' in row and type(row['tsky']) != float:
        # Early TESS4C did not transmit temperatures
        raise ReadingTypeError('tsky', float, type(row['tsky']))
    if 'tamb' in row and type(row['tamb']) != float:
        raise ReadingTypeError('tamb', float, type(row['tamb']))
    _validateCommonReadingsOptionals(row)


__all__ = [
    "validateRegisterTESSW",
    "validateReadingsTESSW",
    "validateRegisterTESS4C",
    "validateReadingsTESS4C",
]
