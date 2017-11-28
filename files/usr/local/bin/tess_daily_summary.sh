#!/bin/bash
# Summary report by instrument

# ------------------------------------------------------------------------------
#                             AUXILIARY FUNCTIONS
# ------------------------------------------------------------------------------

report_by_tess() {
dbase=$1
sqlite3 ${dbase} <<EOF 
.mode column
.headers on
SELECT d.sql_date, i.name, count(*) AS readings
FROM tess_readings_t AS r
JOIN tess_t AS i USING (tess_id)
JOIN date_t AS d USING (date_id)
GROUP BY r.date_id, r.tess_id
ORDER BY d.sql_date DESC, CAST(substr(i.name, 6) as decimal) ASC;
EOF
}

# ------------------------------------------------------------------------------

# may be we need it ..
TODAY=$(date +%Y%m%d)

# Arguments from the command line & default values
dbase="${1:-/var/dbase/tess.db}"
out_dir="${2:-/var/dbase/reports}"

# get the name from the script name without extensions
name=$(basename ${0%.sh})

if  [[ ! -f $dbase || ! -r $dbase ]]; then
        echo "Database file $dbase does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

/usr/sbin/service tessdb pause
sleep 2
report_by_tess ${dbase} > ${out_dir}/${name}.txt
/usr/sbin/service tessdb resume
