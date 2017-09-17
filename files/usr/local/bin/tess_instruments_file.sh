#!/bin/bash
# {{ ansible_managed }}

# Arguments from the command line & default values
dbase="${1:-/var/dbase/tess.db}"
instruments_file="${2:-/var/dbase/tess_instruments.txt}"

sqlite3 ${dbase} <<EOF
SELECT name 
FROM tess_t 
WHERE name like 'stars%' 
AND valid_state = 'Current' 
ORDER by name ASC;
EOF
}

service tessdb pause
sleep 2
query_names > ${instruments_file}
service tessdb resume