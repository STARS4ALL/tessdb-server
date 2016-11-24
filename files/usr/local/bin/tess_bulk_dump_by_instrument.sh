#!/bin/bash
#
# Bulk dump by insterument name

instrument_name=$1

sqlite3 -csv -header /var/dbase/tess.db <<EOF
SELECT (d.julian_day + t.day_fraction) AS julian_day, (d.sql_date || 'T' || t.time) AS timestamp, r.sequence_number, l.site, i.name, r.frequency, r.magnitude, i.zero_point, r.sky_temperature, r.ambient_temperature
FROM tess_readings_t AS r
JOIN tess_t          AS i USING (tess_id)
JOIN location_t      AS l USING (location_id)
JOIN date_t          AS d USING (date_id)
JOIN time_t          AS t USING (time_id)
WHERE i.name = "${instrument_name}"
ORDER BY r.date_id ASC, r.time_id ASC;
EOF
