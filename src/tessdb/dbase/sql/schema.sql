------------------------------------------------------------
--          TESSDB DATA MODEL
------------------------------------------------------------

BEGIN TRANSACTION;

-- --------------------------------------------------------------
-- Miscelaneous configuration not found in the configuration file
-- --------------------------------------------------------------

CREATE TABLE IF NOT EXISTS config_t
(
    section        TEXT NOT NULL,  -- Configuration section
    property       TEXT NOT NULL,  -- Property name
    value          TEXT NOT NULL,  -- Property value
    PRIMARY KEY(section, property)
);

INSERT OR REPLACE INTO config_t(section, property, value) VALUES ('database', 'version', '04');

-- --------------
-- Date dimension
-- --------------

CREATE TABLE IF NOT EXISTS date_t 
(
    date_id        INTEGER NOT NULL, 
    sql_date       TEXT    NOT NULL, 
    date           TEXT    NOT NULL,
    day    		   INTEGER NOT NULL,
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

-- -------------------------
-- Time of the Day dimension
-- -------------------------

CREATE TABLE IF NOT EXISTS time_t
(
    time_id        INTEGER NOT NULL, 
    time           TEXT    NOT NULL,
    hour           INTEGER NOT NULL,
    minute         INTEGER NOT NULL,
    second         INTEGER NOT NULL,
    day_fraction   REAL    NOT NULL,
    PRIMARY KEY(time_id)
);

-- ------------------
-- Location dimension
-- ------------------

CREATE TABLE IF NOT EXISTS location_t
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

INSERT OR IGNORE INTO location_t (location_id,longitude,latitude,elevation,place,town,sub_region,region,country,timezone)
VALUES (-1,NULL,NULL,NULL,'Unknown','Unknown','Unknown','Unknown','Unknown','Etc/UTC');

-- ------------------
-- Observer dimension
-- ------------------

-- --------------------------------------------------------------------------------
-- This table is a mix-in from indiduals and organizations in a flat table
-- Versioned attributed are for individuals only (they may change organiztaions) 
-- and include:
--   1) affiliation, 2) acronym, 3) email, 4) website_url
-----------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS observer_t
(
    observer_id     INTEGER NOT NULL,
    type    TEXT NOT NULL,    -- Observer category: 'Individual' or 'Organization'
    name    TEXT NOT NULL,    -- Individual full name / Organization name 
    affiliation     TEXT,     -- Individual affiliation if individual belongs to an organization
    acronym         TEXT,     -- Organization acronym (i.e. AAM). Also may be applied to affiliation
    website_url     TEXT,     -- Individual / Organization Web page
    email           TEXT,     -- Individual / Organization contact email
    valid_since     TIMESTAMP NOT NULL,  -- versioning attributes, start timestamp, ISO8601
    valid_until     TIMESTAMP NOT NULL,  -- versioning attributes, end  timestamp, ISO8601
    valid_state     TEXT NOT NULL,       -- versioning attributes,state either 'Current' or 'Expired'
 
    UNIQUE(name,valid_since,valid_until),
    PRIMARY KEY(observer_id)
);

INSERT OR IGNORE INTO observer_t (observer_id, name, type, valid_since, valid_until, valid_state)
VALUES (-1, 'Unknown', 'Organization', '2000-01-01 00:00:00.000', '2999-12-31 23:59:59.000', 'Current');

-- -----------------------------------
-- Miscelaneous dimension (flags, etc)
-- -----------------------------------

CREATE TABLE IF NOT EXISTS tess_units_t
(
    units_id          INTEGER NOT NULL, 
    timestamp_source  TEXT    NOT NULL,
    reading_source    TEXT    NOT NULL,
    PRIMARY KEY(units_id)
);

INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES (0, 'Subscriber', 'Direct');
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES (1, 'Publisher',  'Direct');
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES (2, 'Subscriber', 'Imported');
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES (3, 'Publisher',  'Imported');

-- ------------------------
-- The Instrument dimension
-- ------------------------

-----------------------------------------------------------
-- Default values are used for the old registration message
-----------------------------------------------------------

CREATE TABLE IF NOT EXISTS tess_t
(
    tess_id       INTEGER,
    mac_address   TEXT    NOT NULL,             -- Device MAC address
    valid_since   TIMESTAMP NOT NULL,           -- versioning attributes, start timestamp, ISO8601
    valid_until   TIMESTAMP NOT NULL,           -- versioning attributes, end  timestamp, ISO8601
    valid_state   TEXT    NOT NULL,             -- versioning attributes,state either 'Current' or 'Expired'
    model         TEXT    NOT NULL,             -- Either 'TESS-W', 'TESS4C'
    firmware      TEXT    NOT NULL,             -- Firmware version string + compilation date string if available.
    authorised    INTEGER NOT NULL,             -- Flag 1 = Authorised, 0 not authorised
    registered    TEXT    NOT NULL,             -- Either 'Manual' or 'Auto' or 'Unknown' in the worst case
    cover_offset  REAL    NOT NULL DEFAULT 0.0,       -- Deprecated
    fov           REAL    NOT NULL DEFAULT 17.0,      -- Deprecated
    azimuth       REAL    NOT NULL DEFAULT 0.0,       -- Deprecated
    altitude      REAL    NOT NULL DEFAULT 90.0,      -- Deprecated
    nchannels     INTEGER NOT NULL,   -- 1 to 4
    zp1           REAL    NOT NULL,             -- Zero Point 1
    filter1       TEXT    NOT NULL,             -- Filter 1 name (i.e. UV/IR-740, R, G, B)
    offset1       REAL    NOT NULL DEFAULT 0.0, -- Frequency 1 offset in Hz
    zp2           REAL,                         -- Zero Point 2
    filter2       TEXT,                         -- Filter 2 name (i.e. UV/IR-740, R, G, B)
    offset2       REAL    NOT NULL DEFAULT 0.0, -- Frequency 2 offset in Hz
    zp3           REAL ,                        -- Zero Point 3
    filter3       TEXT,                         -- Filter 3 name (i.e. UV/IR-740, R, G, B)
    offset3       REAL    NOT NULL DEFAULT 0.0, -- Frequency 3 offset in Hz
    zp4           REAL,                         -- Zero Point 4
    filter4       TEXT,                         -- Filter 4 name (i.e. UV/IR-740, R, G, B)
    offset4       REAL    NOT NULL DEFAULT 0.0, -- Frequency 4 offset in Hz
    location_id   INTEGER NOT NULL DEFAULT -1,        -- Current location, defaults to unknown location
    observer_id   INTEGER NOT NULL DEFAULT -1,        -- Current observer, defaults to unknown observer
    PRIMARY KEY(tess_id),
    FOREIGN KEY(location_id) REFERENCES location_t(location_id),
    FOREIGN KEY(observer_id) REFERENCES observer_t(observer_id)
);

CREATE INDEX IF NOT EXISTS tess_mac_i ON tess_t(mac_address);

-----------------------------------------------------
-- Names to MACs mapping
-- In the end it is unfortunate that users may change 
-- instrument names and the messages only carry names
-----------------------------------------------------

CREATE TABLE IF NOT EXISTS name_to_mac_t
(
    name          TEXT NOT NULL,
    mac_address   TEXT NOT NULL REFERENCES tess_t(mac_adddres), 
    valid_since   TIMESTAMP NOT NULL,  -- start date when the name,mac association was valid
    valid_until   TIMESTAMP NOT NULL,  -- end date when the name,mac association was valid
    valid_state   TEXT NOT NULL        -- either 'Current' or 'Expired'
);

CREATE INDEX IF NOT EXISTS mac_to_name_i ON name_to_mac_t(mac_address);
CREATE INDEX IF NOT EXISTS name_to_mac_i ON name_to_mac_t(name);

-----------------------------------------------------
-- The TESS-W integrated View
-----------------------------------------------------

CREATE VIEW IF NOT EXISTS tess_v AS SELECT
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
    tess_t.offset1,
    tess_t.zp2,
    tess_t.filter2,
    tess_t.offset2,
    tess_t.zp3,
    tess_t.filter3,
    tess_t.offset3,
    tess_t.zp4,
    tess_t.filter4,
    tess_t.offset4,
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
WHERE name_to_mac_t.valid_state == 'Current';

---------------------------
-- The TESS-W 'Facts' table
---------------------------

CREATE TABLE tess_readings_t
(
    date_id         INTEGER NOT NULL, 
    time_id         INTEGER NOT NULL, 
    tess_id         INTEGER NOT NULL,
    location_id     INTEGER NOT NULL DEFAULT -1,
    observer_id     INTEGER NOT NULL DEFAULT -1,
    units_id        INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL, 
    frequency       REAL    NOT NULL,    
    magnitude       REAL    NOT NULL,
    box_temperature REAL    NOT NULL,
    sky_temperature REAL    NOT NULL,
    azimuth         REAL,    -- optional, in decimal degrees
    altitude        REAL,    -- optional, in decimal degrees
    longitude       REAL,    -- optional, in decimal degrees
    latitude        REAL,    -- optional, in decimal degrees
    elevation       REAL,    -- optional, in decimal degrees
    signal_strength INTEGER NOT NULL, 
    hash            TEXT,    -- optional, to verify readings
 
    PRIMARY KEY(date_id, time_id, tess_id),
    FOREIGN KEY(date_id) REFERENCES date_t(date_id),
    FOREIGN KEY(time_id) REFERENCES time_t(time_id),
    FOREIGN KEY(tess_id) REFERENCES tess_t(tess_id),
    FOREIGN KEY(location_id) REFERENCES location_t(location_id),
    FOREIGN KEY(observer_id) REFERENCES observer_t(observer_id),
    FOREIGN KEY(units_id) REFERENCES tess_units_t(units_id)
);

-- This is meant for IDA reports
CREATE INDEX IF NOT EXISTS tess_readings_i ON tess_readings_t(tess_id, date_id, time_id, location_id);

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

-- This is meant for IDA reports
CREATE INDEX IF NOT EXISTS tess_id_readings4c_i ON tess_readings4c_t(tess_id, date_id, time_id, location_id);

COMMIT;
