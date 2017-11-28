#!/bin/bash
# This script dumps every reading from every TESS given in an instrument list file.

# ------------------------------------------------------------------------------
#                             AUXILIARY FUNCTIONS
# ------------------------------------------------------------------------------

query_names() {
dbase=$1
sqlite3 ${dbase} <<EOF
SELECT name 
FROM tess_t 
WHERE name like 'stars%' 
AND valid_state = 'Current' 
ORDER by name ASC;
EOF
}

# ------------------------------------------------------------------------------- #

bulk_dump_by_instrument() {
instrument_name=$1
sqlite3 -csv -header ${dbase} <<EOF
.separator ;
SELECT (d.julian_day + t.day_fraction) AS julian_day, (d.sql_date || 'T' || t.time || 'Z') AS timestamp, r.sequence_number, l.site, i.name, r.frequency, r.magnitude, i.zero_point, i.filter, r.sky_temperature, r.ambient_temperature
FROM tess_readings_t AS r
JOIN tess_t          AS i USING (tess_id)
JOIN location_t      AS l USING (location_id)
JOIN date_t          AS d USING (date_id)
JOIN time_t          AS t USING (time_id)
WHERE i.name = "${instrument_name}"
ORDER BY r.date_id ASC, r.time_id ASC;
EOF
}

# ------------------------------------------------------------------------------- #

# Arguments from the command line & default values
dbase="${1:-/var/dbase/tess.db}"
out_dir="${2:-/var/dbase/reports}"

if  [[ ! -f $dbase || ! -r $dbase ]]; then
        echo "Database file $dbase does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

if  [[ ! -d $out_dir  ]]; then
        echo "Output directory $out_dir does not exists."
        echo "Exiting"
        exit 1
fi




# Stops background database I/O
/usr/sbin/service tessdb pause 
sleep 2
photometers=$(query_names ${dbase})
# Loops over the instruments file and dumping data
for instrument in $photometers; do
        echo "Generating compresed CSV for TESS $instrument"
        bulk_dump_by_instrument ${instrument} ${dbase} | gzip > ${out_dir}/${instrument}.csv.gz
done

# Resume background database I/O
/usr/sbin/service tessdb resume
