#!/bin/bash
# today's unrise/sunset for all  locations

name=$(basename $0 .sh)
suffix=$(/bin/date +%Y%m%dT%H%M00)
out_dir=/var/dbase/reports

sqlite3 /var/dbase/tess.db <<EOF > ${out_dir}/${name}.${suffix}.txt
.headers on
.mode column
SELECT i.name, l.site, l.sunrise, l.sunset
FROM tess_t     AS i
JOIN location_t AS l USING (location_id)
WHERE i.calibrated_state = 'Current'
ORDER BY i.name ASC;
EOF
