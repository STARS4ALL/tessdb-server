# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import os
import os.path
import uuid
import sqlite3
import shutil
import subprocess

from contextlib import closing
from importlib.resources import files

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

# -------------------
# Third party imports
# -------------------

# --------------
# local imports
# -------------

from . import NAMESPACE

# ----------------
# Module constants
# ----------------

# Database resources
SQL_SCHEMA = files("tessdb.dbase.sql").joinpath("schema.sql")
SQL_INITIAL_DATA_DIR = files("tessdb.dbase.sql.initial")
try:
    SQL_UPDATES_DATA_DIR = files("tessdb.dbase.sql.updates")
except ModuleNotFoundError:
    SQL_UPDATES_DATA_DIR = None  # When there are no updates

# --------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

VERSION_QUERY = "SELECT value from config_t WHERE section ='database' AND property = 'version'"

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------


def _filter_factory(connection):
    cursor = connection.cursor()
    cursor.execute(VERSION_QUERY)
    result = cursor.fetchone()
    if not result:
        raise NotImplementedError(VERSION_QUERY)
    version = int(result[0])
    return lambda path: int(os.path.basename(path)[:2]) > version


# -------------------------
# Module private functions
# -------------------------


def _execute_script(dbase_path, sql_path_obj):
    log.info("Applying updates to data model from {path}", path=sql_path_obj)
    try:
        connection = sqlite3.connect(dbase_path)
        connection.executescript(sql_path_obj.read_text())
    except sqlite3.OperationalError:
        connection.close()
        log.error("Error using the Python API. Trying with sqlite3 CLI")
        sqlite_cli = shutil.which("sqlite3")
        _ = subprocess.check_call([sqlite_cli, dbase_path, "-init", sql_path_obj])
    else:
        connection.close()


def _create_database(dbase_path):
    """Creates a Database file if not exists and returns a connection"""
    new_database = False
    output_dir = os.path.dirname(dbase_path)
    if not output_dir:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(dbase_path):
        with open(dbase_path, "w"):
            pass
        new_database = True
    sqlite3.connect(dbase_path).close()
    return new_database


def _create_schema(
    dbase_path,
    schema_resource,
    initial_data_dir_path,
    updates_data_dir,
    query=VERSION_QUERY,
):
    created = True
    with closing(sqlite3.connect(dbase_path)) as connection:
        with closing(connection.cursor()) as cursor:
            try:
                cursor.execute(query)
            except Exception:
                created = False
        if not created:
            connection.executescript(schema_resource.read_text())
            # the filtering part is because Python 3.9 resource folders cannot exists without __init__.py
            file_list = [
                sql_file
                for sql_file in initial_data_dir_path.iterdir()
                if not sql_file.name.startswith("__") and not sql_file.is_dir()
            ]
            for sql_file in file_list:
                connection.executescript(sql_file.read_text())
        elif updates_data_dir is not None:
            filter_func = _filter_factory(connection)
            # the filtering part is beacuse Python 3.9 resource folders cannot exists without __init__.py
            file_list = sorted(
                [
                    sql_file
                    for sql_file in updates_data_dir.iterdir()
                    if not sql_file.name.startswith("__") and not sql_file.is_dir()
                ]
            )
            file_list = list(filter(filter_func, file_list))
            for sql_file in file_list:
                _execute_script(dbase_path, sql_file)
        else:
            file_list = list()
    return not created, file_list


# -------------------------
# UUID and version handling
# -------------------------


def _read_database_version(connection):
    cursor = connection.cursor()
    query = "SELECT value FROM config_t WHERE section = 'database' AND property = 'version'"
    cursor.execute(query)
    version = cursor.fetchone()[0]
    return version


def _write_database_uuid(connection):
    guid = str(uuid.uuid4())
    cursor = connection.cursor()
    param = {"section": "database", "property": "uuid", "value": guid}
    cursor.execute(
        """
        INSERT INTO config_t(section,property,value) 
        VALUES(:section,:property,:value)
        """,
        param,
    )
    connection.commit()
    return guid


def _make_database_uuid(connection):
    cursor = connection.cursor()
    query = "SELECT value FROM config_t WHERE section = 'database' AND property = 'uuid'"
    cursor.execute(query)
    guid = cursor.fetchone()
    if guid:
        try:
            uuid.UUID(guid[0])  # Validate UUID
        except ValueError:
            guid = _write_database_uuid(connection)
        else:
            guid = guid[0]
    else:
        guid = _write_database_uuid(connection)
    return guid


# ----------------
# Exported funtion
# ----------------


def create_or_open_database(url):
    new_database = _create_database(url)
    if new_database:
        log.warn("Created new database file with initial schema: {url}", url=url)
    just_created, file_list = _create_schema(
        url, SQL_SCHEMA, SQL_INITIAL_DATA_DIR, SQL_UPDATES_DATA_DIR
    )
    if just_created:
        for sql_file in file_list:
            log.warn("Populated data model from {url}", url=os.path.basename(sql_file))
    else:
        for sql_file in file_list:
            log.warn(
                "Applied updates to data model from {url}",
                url=os.path.basename(sql_file),
            )
    connection = sqlite3.connect(url)
    version = _read_database_version(connection)
    guid = _make_database_uuid(connection)
    log.warn(
        "Open database: {url}, data model version = {version}, UUID = {uuid}",
        url=url,
        version=version,
        uuid=guid,
    )
    connection.commit()
    return connection


__all__ = [
    "create_or_open_database",
]
