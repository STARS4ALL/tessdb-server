------------------------------------------------------------
--          TESSDB DATA MODEL
------------------------------------------------------------

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


-- --------------
-- Date dimension
-- --------------

CREATE TABLE IF NOT EXISTS date_t 
(
    date_id        INTEGER PRIMARY KEY, 
    sql_date       TEXT, 
    date           TEXT,
    day    		   INTEGER,
    day_year       INTEGER,
    julian_day     REAL,
    weekday        TEXT,
    weekday_abbr   TEXT,
    weekday_num    INTEGER,
    month_num      INTEGER,
    month          TEXT,
    month_abbr     TEXT,
    year           INTEGER
);

-- -------------------------
-- Time of the Day dimension
-- -------------------------

CREATE TABLE IF NOT EXISTS time_t
(
    time_id        INTEGER PRIMARY KEY, 
    time           TEXT,
    hour           INTEGER,
    minute         INTEGER,
    second         INTEGER,
    day_fraction   REAL
);

-- ------------------
-- Location dimension
-- ------------------

CREATE TABLE IF NOT EXISTS location_t
(
    location_id     INTEGER PRIMARY KEY AUTOINCREMENT,  
    site            TEXT,
    longitude       REAL,
    latitude        REAL,
    elevation       REAL,
    zipcode         TEXT,
    location        TEXT,
    province        TEXT,
    state           TEXT,
    country         TEXT,
    timezone        TEXT DEFAULT 'Etc/UTC',
    contact_name    TEXT,
    contact_email           TEXT,
    organization    TEXT
);

-- -----------------------------------
-- Miscelaneous dimension (flags, etc)
-- -----------------------------------

CREATE TABLE IF NOT EXISTS tess_units_t
(
    units_id          INTEGER PRIMARY KEY AUTOINCREMENT, 
    timestamp_source  TEXT,
    reading_source    TEXT
);

-- ------------------------
-- The Instrument dimension
-- ------------------------

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

CREATE INDEX IF NOT EXISTS tess_mac_i ON tess_t(mac_address);

CREATE VIEW IF NOT EXISTS tess_v AS SELECT
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
    location_t.timezone
FROM tess_t 
JOIN location_t    USING (location_id)
JOIN name_to_mac_t USING (mac_address)
WHERE name_to_mac_t.valid_state == "Current";

-----------------------------------------------------
-- Names to MACs mapping
-- In the end it is unfortunate that users may change 
-- instrument names and the messages only carry names
-----------------------------------------------------

CREATE TABLE IF NOT EXISTS name_to_mac_t
(
    name          TEXT NOT NULL,
    mac_address   TEXT NOT NULL REFERENCES tess_t(mac_adddres), 
    valid_since   TEXT NOT NULL,
    valid_until   TEXT NOT NULL,
    valid_state   TEXT NOT NULL 
);

CREATE INDEX IF NOT EXISTS mac_to_name_i ON name_to_mac_t(mac_address);
CREATE INDEX IF NOT EXISTS name_to_mac_i ON name_to_mac_t(name);

-------------------------
-- The main 'Facts' table
-------------------------

CREATE TABLE tess_readings_t
(
    date_id             INTEGER NOT NULL REFERENCES date_t(date_id), 
    time_id             INTEGER NOT NULL REFERENCES time_t(time_id), 
    tess_id             INTEGER NOT NULL REFERENCES tess_t(tess_id),
    location_id         INTEGER NOT NULL REFERENCES location_t(location_id),
    units_id            INTEGER NOT NULL REFERENCES tess_units_t(units_id),
    sequence_number     INTEGER,
    frequency           REAL,
    magnitude           REAL,
    ambient_temperature REAL,
    sky_temperature     REAL,
    azimuth             REAL,
    altitude            REAL,
    longitude           REAL,
    latitude            REAL,
    height              REAL, 
    signal_strength     INTEGER,
    hash                TEXT, -- to verify readings

    PRIMARY KEY (date_id, time_id, tess_id)
);
