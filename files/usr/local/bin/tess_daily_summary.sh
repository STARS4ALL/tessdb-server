#!/bin/bash
# Summary report by instrument

# may be we need it ..
TODAY=$(date +%Y%m%d)

# Arguments from the command line & default values
dbase="${1:-/var/dbase/tess.db}"


if  [[ ! -f $dbase || ! -r $dbase ]]; then
        echo "Database file $dbase does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

service tessdb pause
sleep 2

sqlite3 ${dbase} <<EOF
.mode column
.headers on
SELECT d.sql_date, i.name, count(*) AS readings
FROM tess_readings_t AS r
JOIN tess_t AS i USING (tess_id)
JOIN date_t AS d USING (date_id)
GROUP BY r.date_id, r.tess_id
ORDER BY d.sql_date DESC;
EOF

service tessdb resume
