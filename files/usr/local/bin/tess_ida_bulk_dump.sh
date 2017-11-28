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

# We use a backup copy to avoid disrupting the operational database for such a long process time
dbase="$(ls -1 /var/dbase/tess.db-*)"

# Output directory is created if not exists inside the inner script
out_dir="${1:-/var/dbase/reports/IDA}"

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


# Stops background database I/O (DON'T NEED THIS IN A BACKUP COPY)
#/usr/sbin/service tessdb pause 
#sleep 2

photometers=$(query_names ${dbase})
# Loops over the instruments file and dumping data
for instrument in $photometers; do
    echo "Generating latest month IDA file for TESS $instrument under ${out_dir}/${instrument}"
    /usr/local/bin/tess_ida ${instrument} -l -d ${dbase} -t ${template} -o ${out_dir} 
done

# Resume background database I/O
#/usr/sbin/service tessdb resume (DON'T NEED THIS IN A BACKUP COPY)
