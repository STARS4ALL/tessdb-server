#!/bin/bash
# This script creates indices for reports.

# ------------------------------------------------------------------------------
#                             AUXILIARY FUNCTIONS
# ------------------------------------------------------------------------------

create_indices() {
dbase=$1
sqlite3 ${dbase} <<EOF
CREATE INDEX IF NOT EXISTS tess_readings_i ON tess_readings_t(tess_id,location_id,date_id,time_id);
EOF
}

# ------------------------------------------------------------------------------- #

# Arguments from the command line & default values

# wildcard expansion ...
dbase="$(ls -1 /var/dbase/tess.db-*)"


if  [[ ! -f $dbase || ! -r $dbase ]]; then
        echo "Database file $dbase does not exists or is not readable."
        echo "Exiting"
        exit 1
fi


echo "Generating indexes for queries in database ${dbase}"
create_indices ${dbase}
