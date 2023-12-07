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
    acronym         TEXT,             -- Organization acronym (i.e. AAM). Also may be applied to affiliation
    website_url     TEXT,             -- Individual / Organization Web page
    email           TEXT,             -- Individual / Organization contact email
    valid_since     TIMESTAMP NOT NULL,  -- versioning attributes, start timestamp, ISO8601
    valid_until     TIMESTAMP NOT NULL,  -- versioning attributes, end  timestamp, ISO8601
    valid_state     TEXT NOT NULL,    -- versioning attributes,state either 'Current' or 'Expired'
 
    UNIQUE(name,valid_since,valid_until),
    PRIMARY KEY(observer_id)
);

INSERT INTO observer_t (observer_id, name, type, valid_since, valid_until, valid_state)
VALUES (-1, 'Unknown', 'Organization', '2000-01-01T00:00:00', '2999-12-31T23:59:59', 'Current');


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
    zp3           REAL ,                              -- Zero Point 3
    filter3       TEXT,                               -- Filter 3 name (i.e. UV/IR-740, R, G, B)
    zp4           REAL,                               -- Zero Point 4
    filter4       TEXT,                               -- Filter 4 name (i.e. UV/IR-740, R, G, B)
    location_id   INTEGER NOT NULL DEFAULT -1,        -- Current location, defaults to unknown location
    observer_id   INTEGER NOT NULL DEFAULT -1,        -- Current observer, defaults to unknown observer
    PRIMARY KEY(tess_id),
    FOREIGN KEY(location_id)    REFERENCES location_t(location_id),
    FOREIGN KEY(observer_id)    REFERENCES observer_t(observer_id)
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
    sequence_number INTEGER,  -- This should be NOT NULL. However, it is a pain to migrate this table
    freq1           REAL,     -- This should be NOT NULL. However, it is a pain to migrate this table
    mag1            REAL,     -- This should be NOT NULL. However, it is a pain to migrate this table
    freq2           REAL,
    mag2            REAL,
    freq3           REAL,
    mag3            REAL,
    freq4           REAL,
    mag4            REAL,
    box_temperature REAL,
    sky_temperature REAL,
    azimuth         REAL,   -- decimal degrees
    altitude        REAL,   -- decimal degrees
    longitude       REAL,   -- decimal degrees
    latitude        REAL,   -- decimal degrees
    elevation       REAL,   -- meters above sea level
    signal_strength INTEGER,
    hash            TEXT,   -- to verify readings

    PRIMARY KEY (date_id, time_id, tess_id),
    FOREIGN KEY(date_id) REFERENCES date_t(date_id),
    FOREIGN KEY(time_id) REFERENCES time_t(time_id),
    FOREIGN KEY(tess_id) REFERENCES tess_t(tess_id),
    FOREIGN KEY(location_id) REFERENCES location_t(location_id),
    FOREIGN KEY(observer_id) REFERENCES observer_t(observer_id),
    FOREIGN KEY(units_id) REFERENCES tess_units_t(units_id)
);


INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '03');

COMMIT;
PRAGMA foreign_keys=ON;