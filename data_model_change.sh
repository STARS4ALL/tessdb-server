#!/bin/bash

sqlite3 /var/dbase/tess.db <<EOF
-- disable foreign key constraint check
PRAGMA foreign_keys=off;
 
-- start a transaction
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS tess_new_t
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

CREATE TABLE IF NOT EXISTS tess_units_new_t
            (
            units_id                  INTEGER PRIMARY KEY AUTOINCREMENT, 
            timestamp_source          TEXT,
            reading_source            TEXT
            );

CREATE TABLE IF NOT EXISTS location_new_t
            (
            location_id             INTEGER PRIMARY KEY AUTOINCREMENT,  
            site                    TEXT,
            longitude               REAL,
            latitude                REAL,
            elevation               REAL,
            zipcode                 TEXT,
            location                TEXT,
            province                TEXT,
            state                   TEXT,
            country                 TEXT,
            timezone                TEXT DEFAULT 'Etc/UTC',
            contact_name            TEXT,
            contact_email           TEXT,
            organization            TEXT
            );

-- copy data from the tess_t table to the new_table
INSERT INTO tess_new_t(tess_id,mac_address,zero_point,filter,valid_since,valid_until,valid_state,location_id,
model,firmware,channel,cover_offset,fov,azimuth,altitude,authorised,registered)
SELECT tess_id,mac_address,zero_point,filter,valid_since,valid_until,valid_state,location_id,
model,firmware,channel,cover_offset,fov,azimuth,altitude,authorised,registered
FROM tess_t;
 
-- copy data from the location_t table to the new_table
INSERT INTO location_new_t(location_id,site,longitude,latitude,elevation,zipcode,location,province,country,
timezone,contact_name,contact_email,organization)
SELECT location_id,site,longitude,latitude,elevation,zipcode,location,province,country,
timezone,contact_name,contact_email,organization FROM location_t;

-- copy data from the tess_units_t table to the new_table
INSERT INTO tess_units_new_t(units_id,timestamp_source,reading_source)
SELECT units_id,timestamp_source,reading_source FROM tess_units_t;

-- drop the tables
DROP TABLE tess_t;
DROP TABLE location_t;
DROP TABLE tess_units_t;

 
-- rename the new_tables to the old table names
ALTER TABLE tess_new_t RENAME TO tess_t; 
ALTER TABLE location_new_t RENAME TO location_t;
ALTER TABLE tess_units_new_t RENAME TO tess_units_t; 
 
UPDATE tess_t
SET filter = 'UV/IR-cut'
WHERE filter = 'UVIR';

UPDATE tess_t
SET filter = 'UV/IR-cut+BG39'
WHERE filter = 'UVIR+BG39';

UPDATE tess_t
SET filter = 'UV/IR-cut+GG495'
WHERE filter = 'UVIR+GG495';

-- commit the transaction
COMMIT;
 
-- enable foreign key constraint check
PRAGMA foreign_keys=on;
EOF
