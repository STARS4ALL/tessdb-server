#!/bin/bash
# {{ ansible_managed }}

# Arguments from the command line & default values
dbase="${1:-/var/dbase/tess.db}"
instruments_file="${2:-/var/dbase/tess_instruments_file.txt}"


if  [[ ! -f $instruments_file || ! -r $instruments_file ]]; then
        echo "Instrument file $instruments_file does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

if  [[ ! -f $dbase || ! -r $dbase ]]; then
        echo "Database file $dbase does not exists or is not readable."
        echo "Exiting"
        exit 1
fi

query_names() {
sqlite3 ${dbase} <<EOF
SELECT name 
FROM tess_t 
WHERE name like 'stars%' 
AND valid_state = 'Current' 
ORDER by name ASC;
EOF
}

/usr/sbin/service tessdb pause
sleep 2
query_names > ${instruments_file}
/usr/sbin/service tessdb resume