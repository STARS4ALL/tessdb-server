PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- ----------------------
-- Schema version upgrade
-- ----------------------

DROP VIEW tess_v;

-- --------------------------------------------------------------------------------
-- New observer table is a mix-in from indiduals and organizations in a flat table
-- Versioned attributed are for individuals only (they may change organiztaions) 
-- and include:
--   1) affiliation, 2) acronym, 3) email, 4) website_url
-----------------------------------------------------------------------------------

CREATE TABLE observer_t
(
    observer_id     INTEGER,
    type            TEXT NOT NULL,    -- Observer category: 'Individual' or 'Organization'
    name            TEXT NOT NULL,    -- Individual full name / Organization name 
    affiliation     TEXT,             -- Individual affiliation if individual belongs to an organization
    acronym         TEXT,             -- Organization or affiliation acronym (i.e. AAM).
    website_url     TEXT,             -- Individual / Organization Web page
    email           TEXT,             -- Individual / Organization contact email
    valid_since     TIMESTAMP NOT NULL,  -- versioning attributes, start timestamp, 
    valid_until     TIMESTAMP NOT NULL,  -- versioning attributes, end  timestamp, 
    valid_state     TEXT NOT NULL,    -- versioning attributes,state either 'Current' or 'Expired'
 
    UNIQUE(name,valid_until),
    PRIMARY KEY(observer_id)
);

INSERT INTO observer_t (observer_id, name, type, valid_since, valid_until, valid_state)
VALUES (-1, 'Unknown', 'Organization', '2000-01-01 00:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');


--------------------------------------------------------------------------------------------
-- SLIGHTLY MODIFIED DATE TABLE, WITH NOT NULLS
-- As per https://sqlite.org/lang_altertable.html
--    1. Create new table
--    2. Copy data
--    3. Drop old table
--    4. Rename new into old
--------------------------------------------------------------------------------------------


CREATE TABLE IF NOT EXISTS date_new_t 
(
    date_id        INTEGER NOT NULL, 
    sql_date       TEXT    NOT NULL, 
    date           TEXT    NOT NULL,
    day            INTEGER NOT NULL,
    day_year       INTEGER NOT NULL,
    julian_day     REAL    NOT NULL,
    weekday        TEXT    NOT NULL,
    weekday_abbr   TEXT    NOT NULL,
    weekday_num    INTEGER NOT NULL,
    month_num      INTEGER NOT NULL,
    month          TEXT    NOT NULL,
    month_abbr     TEXT    NOT NULL,
    year           INTEGER NOT NULL,
    PRIMARY KEY(date_id)
);

INSERT INTO date_new_t SELECT * FROM date_t;
DROP TABLE date_t;
ALTER TABLE date_new_t RENAME TO date_t;

--------------------------------------------------------------------------------------------
-- SLIGHTLY MODIFIED TIME TABLE, WITH NOT NULLS
-- As per https://sqlite.org/lang_altertable.html
--    1. Create new table
--    2. Copy data
--    3. Drop old table
--    4. Rename new into old
--------------------------------------------------------------------------------------------


CREATE TABLE time_new_t
(
    time_id        INTEGER NOT NULL, 
    time           TEXT    NOT NULL,
    hour           INTEGER NOT NULL,
    minute         INTEGER NOT NULL,
    second         INTEGER NOT NULL,
    day_fraction   REAL    NOT NULL,
    PRIMARY KEY(time_id)
);

INSERT INTO time_new_t SELECT * FROM time_t;
DROP TABLE time_t;
ALTER TABLE time_new_t RENAME TO time_t;

--------------------------------------------------------------------------------------------
-- SLIGHTLY UNITS TABLE, WITH NOT NULLS
-- As per https://sqlite.org/lang_altertable.html
--    1. Create new table
--    2. Copy data
--    3. Drop old table
--    4. Rename new into old
--------------------------------------------------------------------------------------------


CREATE TABLE tess_units_new_t
(
    units_id          INTEGER NOT NULL, 
    timestamp_source  TEXT    NOT NULL,
    reading_source    TEXT    NOT NULL,
    PRIMARY KEY(units_id)
);

INSERT INTO tess_units_new_t SELECT * FROM tess_units_t;
DROP TABLE IF EXISTS tess_units_t;
ALTER TABLE tess_units_new_t RENAME TO tess_units_t;

--------------------------------------------------------------------------------------------
-- NEW LOCATION TABLE
-- As per https://sqlite.org/lang_altertable.html
--    1. Create new table
--    2. Copy data
--    3. Drop old table
--    4. Rename new into old
--------------------------------------------------------------------------------------------

CREATE TABLE  location_new_t
(
    location_id     INTEGER NOT NULL,  
    longitude       REAL,          -- in floating point degrees
    latitude        REAL,          -- in floating point degrees
    elevation       REAL,          -- meters above sea level
    place           TEXT NOT NULL,
    town            TEXT NOT NULL, -- village, town, city, etc.
    sub_region      TEXT NOT NULL, -- province, etc.
    region          TEXT NOT NULL, -- federal state, etc
    country         TEXT NOT NULL,
    timezone        TEXT NOT NULL,

    contact_name    TEXT,          -- Deprecated. Now, part of observer_t table
    contact_email   TEXT,          -- Deprecated. Now, part of observer_t table
    organization    TEXT,          -- Deprecated. Now, part of observer_t table

    UNIQUE(longitude, latitude), -- The must be unique but they can be NULL
    PRIMARY KEY(location_id)
);

INSERT INTO location_new_t(location_id,longitude,latitude,elevation,place,town,sub_region,region,country,timezone,
    contact_name,contact_email,organization)
SELECT location_id,longitude,latitude,elevation,site,location,province,state,country,timezone,contact_name,contact_email,organization
FROM location_t;

DROP TABLE  location_t;
ALTER TABLE location_new_t RENAME TO location_t;

--------------------------------------------------------------------------------------------
-- NEW TESS PHOTOMETER TABLE
-- As per https://sqlite.org/lang_altertable.html
--    1. Create new table
--    2. Copy data
--    3. Drop old table
--    4. Rename new into old
--------------------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tess_new_t
(
    tess_id       INTEGER,
    mac_address   TEXT    NOT NULL,                   -- Device MAC address
    valid_since   TIMESTAMP NOT NULL,                 -- versioning attributes, start timestamp, ISO8601
    valid_until   TIMESTAMP NOT NULL,                 -- versioning attributes, end  timestamp, ISO8601
    valid_state   TEXT    NOT NULL,                   -- versioning attributes,state either 'Current' or 'Expired'
    model         TEXT    NOT NULL DEFAULT 'TESS-W',  -- Either 'TESS-W', 'TESS4C'
    firmware      TEXT    NOT NULL DEFAULT 'Unknown', -- Firmware version string.
    authorised    INTEGER NOT NULL DEFAULT 0,         -- Flag 1 = Authorised, 0 not authorised
    registered    TEXT    NOT NULL DEFAULT 'Unknown', -- Either 'Manual' or 'Auto'
    cover_offset  REAL    NOT NULL DEFAULT 0.0,       -- Deprecated
    fov           REAL    NOT NULL DEFAULT 17.0,      -- Deprecated
    azimuth       REAL    NOT NULL DEFAULT 0.0,       -- Deprecated
    altitude      REAL    NOT NULL DEFAULT 90.0,      -- Deprecated
    nchannels     INTEGER NOT NULL DEFAULT 1,        -- 1 to 4
    zp1           REAL    NOT NULL,                   -- Zero Point 1
    filter1       TEXT    NOT NULL DEFAULT 'UV/IR-740', -- Filter 1 name (i.e. UV/IR-740, R, G, B)
    zp2           REAL,                               -- Zero Point 2
    filter2       TEXT,                               -- Filter 2 name (i.e. UV/IR-740, R, G, B)
    zp3           REAL,                               -- Zero Point 3
    filter3       TEXT,                               -- Filter 3 name (i.e. UV/IR-740, R, G, B)
    zp4           REAL,                               -- Zero Point 4
    filter4       TEXT,                               -- Filter 4 name (i.e. UV/IR-740, R, G, B)
    location_id   INTEGER NOT NULL DEFAULT -1,        -- Current location, defaults to unknown location
    observer_id   INTEGER NOT NULL DEFAULT -1,        -- Current observer, defaults to unknown observer
    PRIMARY KEY(tess_id),
    FOREIGN KEY(location_id) REFERENCES location_t(location_id),
    FOREIGN KEY(observer_id) REFERENCES observer_t(observer_id)
);

INSERT INTO tess_new_t(tess_id,mac_address,valid_since,valid_until,valid_state,authorised,registered,model,
	firmware,cover_offset,fov,azimuth,altitude,nchannels,zp1,filter1,location_id,observer_id)
    SELECT tess_id,mac_address,valid_since,valid_until,valid_state,authorised,registered,model,
    	firmware,cover_offset,fov,azimuth,altitude,1,zero_point,filter,location_id,-1
    FROM tess_t;

DROP INDEX tess_mac_i;
DROP TABLE tess_t;
ALTER TABLE tess_new_t RENAME TO tess_t;
CREATE INDEX tess_mac_i ON tess_t(mac_address);

-- -----------------------------
-- The name to MAC mapping table
-- -----------------------------

CREATE TABLE IF NOT EXISTS name_to_mac_new_t
(
    name          TEXT NOT NULL,
    mac_address   TEXT NOT NULL REFERENCES tess_t(mac_adddres), 
    valid_since   TIMESTAMP NOT NULL,  -- start date when the name,mac association was valid
    valid_until   TIMESTAMP NOT NULL,  -- end date when the name,mac association was valid
    valid_state   TEXT NOT NULL        -- either 'Current' or 'Expired'
);

INSERT INTO name_to_mac_new_t SELECT * FROM name_to_mac_t;
DROP INDEX IF EXISTS mac_to_name_i;
DROP INDEX IF EXISTS name_to_mac_i;
DROP TABLE name_to_mac_t;
ALTER TABLE name_to_mac_new_t RENAME TO name_to_mac_t;
CREATE INDEX IF NOT EXISTS mac_to_name_i ON name_to_mac_t(mac_address);
CREATE INDEX IF NOT EXISTS name_to_mac_i ON name_to_mac_t(name);

-- -----------------------------
-- The TESS view
-- -----------------------------

CREATE VIEW tess_v AS SELECT
    tess_t.tess_id,
    tess_t.mac_address,
    name_to_mac_t.name,
    tess_t.valid_since,
    tess_t.valid_until,
    tess_t.valid_state,
    tess_t.model,
    tess_t.firmware,
    tess_t.authorised,
    tess_t.registered,
    tess_t.cover_offset,
    tess_t.fov,
    tess_t.azimuth,
    tess_t.altitude,
    tess_t.nchannels,
    tess_t.zp1,
    tess_t.filter1,
    tess_t.zp2,
    tess_t.filter2,
    tess_t.zp3,
    tess_t.filter3,
    tess_t.zp4,
    tess_t.filter4,
    location_t.longitude,
    location_t.latitude,
    location_t.elevation,
    location_t.place,
    location_t.town,
    location_t.sub_region,
    location_t.region,
    location_t.country,
    location_t.timezone,
    observer_t.name,
    observer_t.type,
    observer_t.affiliation,
    observer_t.acronym
FROM tess_t 
JOIN location_t    USING (location_id)
JOIN observer_t    USING (observer_id)
JOIN name_to_mac_t USING (mac_address)
WHERE name_to_mac_t.valid_state == "Current";

---------------------------
-- The TESS-W 'Facts' table
---------------------------

-- We are adding more columns and renaming some old columns

ALTER TABLE tess_readings_t RENAME COLUMN height TO elevation;
ALTER TABLE tess_readings_t RENAME COLUMN ambient_temperature TO box_temperature;
ALTER TABLE tess_readings_t ADD COLUMN observer_id INTEGER NOT NULL DEFAULT -1 REFERENCES observer_t(observer_id);

---------------------------
-- The TESS4C 'Facts' table
---------------------------

CREATE TABLE tess_readings4c_t
(
    date_id         INTEGER NOT NULL, 
    time_id         INTEGER NOT NULL, 
    tess_id         INTEGER NOT NULL,
    location_id     INTEGER NOT NULL DEFAULT -1,
    observer_id     INTEGER NOT NULL DEFAULT -1,
    units_id        INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,  
    freq1           REAL    NOT NULL,    
    mag1            REAL    NOT NULL,
    freq2           REAL    NOT NULL,
    mag2            REAL    NOT NULL,
    freq3           REAL    NOT NULL,
    mag3            REAL    NOT NULL,
    freq4           REAL    NOT NULL,
    mag4            REAL    NOT NULL,
    box_temperature REAL    NOT NULL,
    sky_temperature REAL    NOT NULL,
    azimuth         REAL,   -- optional, in decimal degrees
    altitude        REAL,   -- optional in decimal degrees
    longitude       REAL,   -- optional decimal degrees
    latitude        REAL,   -- optional decimal degrees
    elevation       REAL,   -- optional meters above sea level
    signal_strength INTEGER NOT NULL,
    hash            TEXT,   -- optional, to verify readings

    PRIMARY KEY(date_id, time_id, tess_id),
    FOREIGN KEY(date_id) REFERENCES date_t(date_id),
    FOREIGN KEY(time_id) REFERENCES time_t(time_id),
    FOREIGN KEY(tess_id) REFERENCES tess_t(tess_id),
    FOREIGN KEY(location_id) REFERENCES location_t(location_id),
    FOREIGN KEY(observer_id) REFERENCES observer_t(observer_id),
    FOREIGN KEY(units_id) REFERENCES tess_units_t(units_id)
);

-- Fixes timestamps to match latest convention from tessdb program
UPDATE tess_t SET valid_since = REPLACE(valid_since, 'T', ' ') || '+00:00';
UPDATE tess_t SET valid_since = REPLACE(valid_since, '+00:00+00:00', '+00:00');
UPDATE tess_t SET valid_until = REPLACE(valid_until, 'T', ' ') || '+00:00';
UPDATE tess_t SET valid_until = REPLACE(valid_until, '+00:00+00:00', '+00:00');

UPDATE name_to_mac_t SET valid_since = REPLACE(valid_since, 'T', ' ') || '+00:00';
UPDATE name_to_mac_t SET valid_since = REPLACE(valid_since, '+00:00+00:00', '+00:00');
UPDATE name_to_mac_t SET valid_until = REPLACE(valid_until, 'T', ' ') || '+00:00';
UPDATE name_to_mac_t SET valid_until = REPLACE(valid_until, '+00:00+00:00', '+00:00');

--------------------------
-- Register missing TESS4C
--------------------------
-- stars701
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('CA:FE:28:BE:CA:11', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022 ?', 0, 'Manual', 4, 20.50, 'UVIR750', 20.50, 'UVIR650', 20.50, 'RGB-R', 20.50, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars701', 'CA:FE:28:BE:CA:11', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars703
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('CA:FE:28:BE:CA:12', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022 ?', 0, 'Manual', 4, 20.18, 'UVIR750', 20.28, 'UVIR650', 20.38, 'RGB-R', 20.04, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars703', 'CA:FE:28:BE:CA:12', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars704
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('CA:FE:28:BE:CA:13', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022 ?', 0, 'Manual', 4, 20.50, 'UVIR750', 20.50, 'UVIR650', 20.50, 'RGB-R', 20.50, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars704',  'CA:FE:28:BE:CA:13', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars705
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('AC:F4:FC:A3:C9:C8', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022 ?', 0, 'Manual', 4, 20.25, 'UVIR750', 20.25, 'UVIR650', 20.25, 'RGB-R', 20.25, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars705',  'AC:F4:FC:A3:C9:C8', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars706
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('A4:C2:FC:A3:C9:C8', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022 ?', 0, 'Manual', 4, 20.24, 'UVIR750', 20.24, 'UVIR650', 20.24, 'RGB-R', 20.24, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars706',  'A4:C2:FC:A3:C9:C8', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars707
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('84:F2:FA:A3:C9:C8', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022 ?', 0, 'Manual', 4, 20.25, 'UVIR750', 20.25, 'UVIR650', 20.25, 'RGB-R', 20.25, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars707',  '84:F2:FA:A3:C9:C8', '2023-12-12 10:00:00+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars854
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('C8:C9:A3:F9:C9:48', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022', 0, 'Manual', 4, 20.03, 'UVIR750', 20.04, 'UVIR650', 19.9, 'RGB-R', 19.8, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars854',  'C8:C9:A3:F9:C9:48', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars855
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('C8:C9:A3:F9:C7:94', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022', 0, 'Manual', 4, 20.03, 'UVIR750', 20.04, 'UVIR650', 19.9, 'RGB-R', 19.8, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars855',  'C8:C9:A3:F9:C7:94', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars856
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('C8:C9:A3:FC:EB:50', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022', 0, 'Manual', 4, 20.03, 'UVIR750', 20.04, 'UVIR650', 19.9, 'RGB-R', 19.8, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars856',  'C8:C9:A3:FC:EB:50', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars857
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('C8:C9:A3:FC:EB:F4', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 28 2022', 0, 'Manual', 4, 20.03, 'UVIR750', 20.04, 'UVIR650', 19.9, 'RGB-R', 19.8, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars857',  'C8:C9:A3:FC:EB:F4', '2023-12-08 21:24:04+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars1081
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('EC:62:60:82:62:9C', '2023-12-08 21:10:43+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Nov 30 2022', 0, 'Manual', 4, 20.08, 'UVIR750', 20.23, 'UVIR650', 20.17, 'RGB-R', 19.84, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars1081', 'EC:62:60:82:62:9C', '2023-12-08 21:10:43+00:00', '2999-12-31 23:59:59+00:00', 'Current');
-- stars1086
INSERT INTO tess_t (mac_address,valid_since,valid_until,valid_state,model,firmware,authorised,registered,nchannels,zp1,filter1,zp2,filter2,zp3,filter3,zp4,filter4,location_id,observer_id) 
VALUES ('EC:62:60:82:70:24', '2023-12-08 21:10:43+00:00', '2999-12-31 23:59:59+00:00', 'Current', 'TESS4C', 'Feb 24 2023', 0, 'Manual', 4, 20.00, 'UVIR750', 20.11, 'UVIR650', 20.07, 'RGB-R', 19.75, 'RGB-B', -1, -1);
INSERT INTO name_to_mac_t(name, mac_address,valid_since,valid_until,valid_state) 
VALUES ('stars1086', 'EC:62:60:82:70:24', '2023-12-08 21:10:43+00:00', '2999-12-31 23:59:59+00:00', 'Current');

-- Upgrades database model version
INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '03');

COMMIT;
PRAGMA foreign_keys=ON;