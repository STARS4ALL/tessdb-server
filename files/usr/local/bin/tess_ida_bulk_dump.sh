#!/bin/bash
# This script dumps latest month readings from every TESS given in an instrument list file.

# Arguments from the command line & default values
instruments_file="${1:-/var/dbase/tess_instruments.txt}"

dbase="${2:-/var/dbase/tess.db}"

# Output directory is created if not exists inside the inner script
out_dir="${3:-/var/dbase/reports/IDA}"

template="${4:-/etc/tessdb/IDA-template.j2}"


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

if  [[ ! -f $template || ! -r $template ]]; then
        echo "IDA Template file $template does not exists or is not readable."
        echo "Exiting"
        exit 1
fi


# Stops background database I/O
/usr/sbin/service tessdb pause 
sleep 2

# Loops over the instruments file and dumping data
for instrument in $( cat $instruments_file ); do
    echo "Generating latest month IDA file for TESS $instrument under ${out_dir}/${instrument}"
    /usr/local/bin/tess_ida ${instrument} -l -d ${dbase} -t ${template} -o ${out_dir} 
done

# Resume background database I/O
/usr/sbin/service tessdb resume
