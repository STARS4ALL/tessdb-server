#!/bin/bash
# today's sunrise/sunset for all locations

# ------------------------------------------------------------------------------
#                             AUXILIARY FUNCTIONS
# ------------------------------------------------------------------------------

query_sunrise_data() {
dbase=$1
sqlite3 ${dbase} <<EOF
.mode line
SELECT i.name, l.site, l.sunrise, l.sunset
FROM tess_t     AS i
JOIN location_t AS l USING (location_id)
WHERE i.valid_state = 'Current'
ORDER BY i.name ASC;
EOF
}
# ------------------------------------------------------------------------------

suffix=$(/bin/date +%Y%m%dT%H%M00)

# Arguments from the command line & default values
name=$(basename $0 .sh)
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

# -------------------
# AUXILIARY FUNCTIONS
# -------------------

/usr/sbin/service tessdb pause 
sleep 2

query_sunrise_data ${dbase} > ${out_dir}/${name}.${suffix}.txt

/usr/sbin/service tessdb resume
