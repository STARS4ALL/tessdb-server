#!/bin/bash
# This script dumps latest month readings from every TESS given in an instrument list file.

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


DEFAULT_DATABASE="/var/dbase/tess.db"
DEFAULT_REPORTS_DIR="/var/dbase/reports/IDA"

# Either the default or the rotated tess.db-* database
dbase="${1:-$DEFAULT_DATABASE}"
# wildcard expansion ...
dbase="$(ls -1 $dbase)"

# Output directory is created if not exists inside the inner script
out_dir="${2:-$DEFAULT_REPORTS_DIR}"

# get the name from the script name without extensions
name=$(basename ${0%.sh})

# Jinja2 template to render IDA format file
template="${2:-/etc/tessdb/IDA-template.j2}"

if  [[ ! -f $dbase || ! -r $dbase ]]; then
        echo "Database file $dbase does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

if  [[ ! -f $template || ! -r $template ]]; then
        echo "IDA Template file $template does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

# Stops background database I/O when using the operational database
if  [[ $dbase = $DEFAULT_DATABASE ]]; then
        echo "Pausing tessdb service."
    	/usr/sbin/service tessdb pause 
		sleep 2
else
	echo "Using backup database, no need to pause tessdb service."
fi

photometers=$(query_names ${dbase})
# Loops over the instruments file and dumping data
for instrument in $photometers; do
    echo "Generating latest month IDA file for TESS $instrument under ${out_dir}/${instrument}"
    /usr/local/bin/tess_ida ${instrument} -l -d ${dbase} -t ${template} -o ${out_dir} 
done


# Resume background database I/O
if  [[ $dbase = $DEFAULT_DATABASE ]]; then
        echo "Resuming tessdb service."
    	/usr/sbin/service tessdb resume 
else
	echo "Using backup database, no need to resume tessdb service."
fi
