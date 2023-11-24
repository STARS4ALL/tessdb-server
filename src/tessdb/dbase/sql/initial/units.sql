BEGIN TRANSACTION;
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES ('0', 'Subscriber', 'Direct');
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES ('1', 'Publisher', 'Direct');
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES ('2', 'Subscriber', 'Imported');
INSERT OR IGNORE INTO tess_units_t (units_id, timestamp_source, reading_source) VALUES ('3', 'Publisher', 'Imported');
COMMIT;
