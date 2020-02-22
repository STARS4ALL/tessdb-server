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

-- copy data from the table to the new_table
INSERT INTO tess_new_t(tess_id,mac_address,zero_point,filter,valid_since,valid_until,valid_state,location_id,
model,firmware,channel,cover_offset,fov,azimuth,altitude,authorised,registered)
SELECT tess_id,mac_address,zero_point,filter,valid_since,valid_until,valid_state,location_id,
model,firmware,channel,cover_offset,fov,azimuth,altitude,authorised,registered
FROM tess_t;
 
INSERT INTO tess_units_new_t(units_id,timestamp_source,reading_source)
SELECT units_id,timestamp_source,reading_source FROM tess_units_t;

-- drop the table
DROP TABLE tess_t;
DROP TABLE tess_units_t;

 
-- rename the new_table to the table
ALTER TABLE tess_new_t RENAME TO tess_t; 
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
