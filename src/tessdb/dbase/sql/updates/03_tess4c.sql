
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- ----------------------
-- Schema version upgrade
-- ----------------------

CREATE TABLE IF NOT EXISTS observer_t
(
    observer_id     INTEGER,
    type            TEXT NOT NULL,    -- Observer category: 'Individual' or 'Organization'
    name            TEXT NOT NULL,    -- Individual full name / Organization name 
    affiliation     TEXT,             -- Individual affiliation if individual belongs to an organization
    acronym         TEXT,             -- Organization acronym (i.e. AAM). Also may be applied to affiliation
    website_url     TEXT,             -- Individual / Organization Web page
    email           TEXT,             -- Individual / Organization contact email
    valid_since     TEXT NOT NULL,    -- versioning attributes, start timestamp, ISO8601
    valid_until     TEXT NOT NULL,    -- versioning attributes, end  timestamp, ISO8601
    valid_state     TEXT NOT NULL,    -- versioning attributes,state either 'Current' or 'Expired'
 
    UNIQUE(name,valid_since,valid_until)

    PRIMARY KEY(observer_id)
);

INSERT OR IGNORE INTO observer_t (observer_id, name, type, valid_since, valid_umtil, valid_state)
VALUES (-1, 'Unknown', 'Organization', '2000-01-01T00:00:00', '2999-12-31T23:59:59', 'Current')

-- As per https://sqlite.org/lang_altertable.html
--    1. Create new table
--    2. Copy data
--    3. Drop old table
--    4. Rename new into old

CREATE TABLE IF NOT EXISTS tess_new_t
(
    tess_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address   TEXT    NOT NULL,                   -- Device MAC address
    valid_since   TEXT    NOT NULL,                   -- versioning attributes, start timestamp, ISO8601
    valid_until   TEXT    NOT NULL,                   -- versioning attributes, end  timestamp, ISO8601
    valid_state   TEXT    NOT NULL,                   -- versioning attributes,state either 'Current' or 'Expired'
    model         TEXT    NOT NULL,                   -- Either 'TESS-W', 'TESS4C'
    firmware      TEXT    NOT NULL DEFAULT 'Umknown', -- Firmware version string.
    authorised    INTEGER NOT NULL,                   -- Flag 1 = Authorised, 0 not authorised
    registered    TEXT    NOT NULL DEFAULT 'Unknown', -- Either 'Manual' or 'Auto'
    cover_offset  REAL    NOT NULL DEFAULT 0.0,       -- Deprecated
    fov           REAL    NOT NULL DEFAULT 17.0,      -- Deprecated
    azimuth       REAL    NOT NULL DEFAULT 0.0,       -- Deprecated
    altitude      REAL    NOT NULL DEFAULT 90.0,      -- Deprecated
    nchannels     INTEGER NOT NULL,                   -- 1 to 4
    zp1           REAL    NOT NULL,                   -- Zero Point 1
    filter1       TEXT    NOT NULL,                   -- Filter 1 name (i.e. UV/IR-740, R, G, B)
    zp2           REAL,                               -- Zero Point 2
    filter2       TEXT,                               -- Filter 2 name (i.e. UV/IR-740, R, G, B)
    zp3           REAL ,                              -- Zero Point 3
    filter4       TEXT,                               -- Filter 3 name (i.e. UV/IR-740, R, G, B)
    zp4           REAL,                               -- Zero Point 4
    filter4       TEXT,                               -- Filter 4 name (i.e. UV/IR-740, R, G, B)
    location_id   INTEGER NOT NULL DEFAULT -1,        -- Current location, defaults to unknown location
    observer_id   INTEGER NOT NULL DEFAULT -1,        -- Current observer, defaults to unknown observer
    FOREIGN KEY(location_id)    REFERENCES location_t(location_id)
    FOREIGN KEY(observer_id)    REFERENCES observer_t(observer_id)
);

INSERT OR IGNORE INTO tess_new_t(tess_id,mac_address,valid_since,valid_until,valid_state,authorised,registered,model,
	firmware,cover_offset,fov,azimuth,altitude,nchannels,zp1,filter1,location_id,observer_id)
SELECT tess_id,mac_address,valid_since,valid_until,valid_state,authorised,registered,model,
	firmware,cover_offset,fov,azimuth,altitude,1,zero_point,filter,location_id,-1
FROM tess_t;

DROP VIEW IF EXISTS tess_v;
DROP TABLE IF EXISTS tess_t;

ALTER TABLE tess_new_t RENAME TO tess_t;


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
    tess_t.zp2,
    tess_t.filter2,
    tess_t.zp3,
    tess_t.filter3,
    tess_t.zp4,
    tess_t.filter4,

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
JOIN observer_t    USING (observer_id)
JOIN name_to_mac_t USING (mac_address)
WHERE name_to_mac_t.valid_state == "Current";


INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '03');

COMMIT;
PRAGMA foreign_keys=ON;