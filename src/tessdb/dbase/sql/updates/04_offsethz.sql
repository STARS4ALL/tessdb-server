PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- ----------------------
-- Schema version upgrade
-- ----------------------

DROP VIEW tess_v;

ALTER TABLE tess_t ADD COLUMN offset1 REAL NOT NULL DEFAULT 0.0;
ALTER TABLE tess_t ADD COLUMN offset2 REAL NOT NULL DEFAULT 0.0;
ALTER TABLE tess_t ADD COLUMN offset3 REAL NOT NULL DEFAULT 0.0;
ALTER TABLE tess_t ADD COLUMN offset4 REAL NOT NULL DEFAULT 0.0;

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

-- Upgrades database model version
INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '04');

COMMIT;
PRAGMA foreign_keys=ON;
