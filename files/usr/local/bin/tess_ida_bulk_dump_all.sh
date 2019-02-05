#!/bin/bash
# This script dumps latest month readings from every TESS given in an instrument list file.
# Cumulative bulk dump since the beginning of the project

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

# get the name from the script name without extensions
name=$(basename ${0%.sh})

# Either the default or the rotated tess.db-* database
dbase="${1:-$DEFAULT_DATABASE}"
# wildcard expansion ...
dbase="$(ls -1 $dbase)"

# Output directory is created if not exists inside the inner script
out_dir="${2:-$DEFAULT_REPORTS_DIR}"

# Jinja2 template to render IDA format file
template="${3:-/etc/tessdb/IDA-template.j2}"

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

dbname=$(basename $dbase)
oper_dbname=$(basename $DEFAULT_DATABASE)

if [[ "$dbname" = "$oper_dbname" ]]; then
    operational_dbase="yes"
else
    operational_dbase="no"
fi


# Stops background database I/O when using the operational database
if  [[ $operational_dbase = "yes" ]]; then
        echo "Pausing tessdb service."
    	/usr/local/bin/tessdb_pause 
		/bin/sleep 2
else
	echo "Using backup database, no need to pause tessdb service."
fi

photometers=$(query_names ${dbase})
years="2015 2016 2017 2018 2019"
months="01 02 03 04 05 06 07 08 09 10 11 12"
# Loops over the instruments file and dumping data
for instrument in $photometers; do
    # Loop over years
    for year in $years; do
        for month in $months; do
            echo "Generating IDA file for TESS $instrument for month $year-$month under ${out_dir}/${instrument}"
            /usr/local/bin/tess_ida ${instrument} -m "${year}-${month}" -d ${dbase} -t ${template} -o ${out_dir}
        done
    done 
done


# Resume background database I/O
if  [[ $operational_dbase = "yes" ]]; then
        echo "Resuming tessdb service."
    	/usr/local/bin/tessdb_resume 
else
	echo "Using backup database, no need to resume tessdb service."
fi
