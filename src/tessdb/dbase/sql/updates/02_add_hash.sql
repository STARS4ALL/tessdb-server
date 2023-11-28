
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- ----------------------
-- Schema version upgrade
-- ----------------------

ALTER TABLE tess_readings_t ADD COLUMN hash TEXT; -- to verify readings

INSERT OR REPLACE INTO config_t(section, property, value) 
VALUES ('database', 'version', '02');


COMMIT;
