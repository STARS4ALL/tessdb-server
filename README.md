# tessdb-server(overview)

Linux service to collect measurements pubished by TESS Sky Quality Meter via MQTT. TESS stands for [Cristobal Garcia's Telescope Encoder and Sky Sensor](http://www.observatorioremoto.com/TESS.pdf)

**tessdb** is being used as part of the [STARS4ALL Project](http://www.stars4all.eu/).

## Description

**tessdb** is a software package that collects measurements from one or several
TESS instruments into database (currently a SQLite Database).  

It is a [Python Twisted Application](https://twistedmatrix.com/trac/)
that uses a [custom Twisted library implementing the MQTT protocol](https://github.com/astrorafael/twisted-mqtt)

Desktop applicatons may query the database to generate reports and graphs
using the accumulated, historic data. There are some reports scripts already included in the package, specially an IDA-format monthly report script.

**Note**: The Windows version has been dropped, as it was never used.

These data sources are available:

+ individual samples (real time, configurable, 1 min. aprox between samples).

Instrument should send their readings at twice the time resolution specified in the config file (in seconds).

**Warning**: Time referencie is always UTC, not local time.

# INSTALLATION
    
## Requirements

The following components are needed and should be installed first:

 * python 2.7.x (tested on Ubuntu Python 2.7.6) or python 3.6+

**Note:** It is foreseen a Python 3 migration in the future, retaining Python 2.7.x compatibility.

### Installation

Installation is done from GitHub:

    git clone https://github.com/astrorafael/tessdb.git
    cd tessdb
    sudo python setup.py install

**Note:** Installation from PyPi is now obsolete. Do not use the package uploaded in PyPi.

* All executables are copied to `/usr/local/bin`
* The database is located at `/var/dbase/tess.db` by default
* The log file is located at `/var/log/tessdb.log`
* The following required PIP packages will be automatically installed:
    - twisted,
    - twisted-mqtt
    - pyephem
    
### Start up and Verification

* Type `sudo tessdb -k` to start the service in foreground with console output.
Verify that it starts without errors or exceptions. When done, abort it with `^C`

From tessdb release 1.2.0, the background execution is handled as a `systemd` service instead of the old system V style init script:

    `sudo systemctl start tessdb`

although the old `sudo service tessdb start` command still works.
* It is strongly recommended to enable the service at boot time by issuing:

`sudo systemctl enable tessdb`

# CONFIGURATION

There is a small configuration file for this service:

* `/etc/tessdb/config` (Linux)

This file is self explanatory. 
In special, the database file name and location is specified in this file.
Some of the properities marked in this file are marked as *reloadable property*. This means that this value can be changed and the process reloads its new value on the fly.

## Sunrise / Sunset filtering

A configurable window (7 samples by default) is stored in the server for each photometer. 
A filter process analyzes the middle sample in this window, if it finds all saturated values (magnitude=0)
around this middle sample (past and future), this sample is discarded, otherwise it is elegible to be written to the database.

*Positive*: This filtering does not need to know the position where the photometer is placed.
*Negative*: There is a time lag (Window size/2) between receiving the sample and storing it.
Furthermore, if the server crashes or is abruptly stopped, the so-called "future samples" are lost.

## Logging

Log file is usually placed under `/var/log/tessdb.log` in Linux or under `C:\tessdb\log` folder on Windows. 
Default log level is `info`. It generates very litte logging at this level.
File is rotated by logrotate **only under Linux**. 

# OPERATION

## Server Status/Start/Stop/Restart

* Service status: `sudo systemctl status tessdb` or `sudo service tessdb status`
* Start Service:  `sudo systemctl start tessdb`  or `sudo service tessdb start`

Strongly recommended:
* Stop Service:    `sudo /usr/local/bin/tessdb_stop`
* Restart Service: `sudo /usr/local/bin/tessdb_restart`

No don use:
* Stop Service:    `sudo systemctl stop tessdb`    or `sudo service tessdb stop`
* Restart Service: `sudo systemctl restart tessdb` or `sudo service tessdb stop`

## Service Pause/Resume

The server can be put in *pause mode*, in which will be still receiving incoming MQTT messages but will be internally enqueued and not written to the database. Also, all connections to the database are closed. This allows to perform high risk operations on the database without loss of incoming data. Examples:

* Compact the database using the SQLite `VACUUM` pragma
* Migrating data from tables.
* etc.

Service pause/resume use internally signals `SIGUSR1` and `SIGUSR2`.

To pause the server, type: `sudo tessdb_pause` and watch the log file output wit `tail -f /var/log/tessdb.log`:

```
2018-11-23T13:08:25+0100 [dbase#info] TESS database writer paused
2018-11-23T13:08:25+0100 [dbase#info] Closed a DB Connection to /var/dbase/tess.db
```

**Note:** The old  `sudo service tessdb pause` command do not work anymore.

To resume normal operation type `sudo tessdb_resume` and watch the same log file:

```
2018-11-23T13:10:37+0100 [dbase#info] TESS database writer resumed
2018-11-23T13:10:37+0100 [dbase#info] Opened a DB Connection to /var/dbase/tess.db
```

##  Service reload

During a reload the service is not stopped and re-reads the new values form the configuration file and apply the changes. In general, all aspects not related to maintaining the current connection to the MQTT broker or changing the database schema can be reloaded. The full list of reloadadble properties is described inside the configuration file.

* Type `sudo systemctl reload tessdb` or `sudo service tessdb reload`. 

## Mainteinance

Database mainteinance is made through the `tess` command line utility, installed by the tessdb-reports package.
Mainteninance operations include:
- create new locations
- create new TESS instruments (manually)
- assign locations to instruments
- enable recording of data received from an instrument
- listing current instruments
- listing instruments not assigned to any known location
- etc.


# DATA MODEL

## Dimensional Modelling

The data model follows the [dimensional modelling]
(https://en.wikipedia.org/wiki/Dimensional_modeling) approach by Ralph Kimball. More references can also be found in [Star Schemas](https://en.wikipedia.org/wiki/Star_schema).

## The data model

The figure below shows the layout of **tessdb**.

![TESS Database Model](doc/tessdb-full.png)

### Dimension Tables

They are:

* `date_t`      : preloaded from 2016 to 2026
* `time_t`      : preloaded, with seconds resolution (configurable)
* `tess_t`      : registered TESS instruments collecting data
* `location_t`  : locations where instruments are deployed
* `tess_units_t`     : an assorted collection of unit labels for reports, preloaded with current units.
* `tess_v`      : View with TESS instrument and current location. It is recommended that reporting applications use this view, instead of the underlying `tess_t` and `location_t` tables.

#### Date Dimension

Pretty much standard date table from dimensional modelling. Contains most used attributes plus `julian_day` specific to Astronomy domain.

#### Time of the day Dimension

Pretty much standard time of the day table from dimensional modelling. Contains well known attributes.

#### Instrument Dimension

This dimension holds the current list of TESS instruments. 

* The real key is an artificial key `tess_id` linked to the Fact table.
* The `mac_address` could be the natural key if it weren't for the zero point and filter history tracking.
* The `location_id` is a reference to the current location assigned to the instrument. Location id -1 denotes the "Unknown" location.
* `model` refers to the current TESS model.
* `firmware` contains the current firmware version.
* `fov` contains the Field of View, in degrees.
* `cover_offset` is an additional offset in mag/arcserc^2 to account for an additional optical window attenuation attached tothe TESS itself. Defaults to 0.0.
* `channel` is the current channel identifier. Default value is 0. Currently, the TESS photometer has only one channel.
* `authorised` to allow the TESS instrument to store readings on the database. Authorization is a manual process done by the *tess utility*.
* `registered` shos if the TESS instrument registered itself on the database ("Automatic") or it was done by a manual process ("Manual") using the *tess utility*. The default value is "Unknown" for the TESS instrument registered before adding this feature to the software. It is expected to identify these cases one by one and set them to 'Manual' or 'Automatic'.

##### Version-controlled Attributes
These attubutes are version-controlled and a historic of these is maintained. A new change in any of them will generate a new row in the `tess_t` table
* The `zero_point` holds the current value of the instrument calibration constant. Defaults to '20.5' (uncalibrated photometer).
* The `filter` holds the current TESS filter (i.e. 'UVIR' or Dichroic Glass). Defaults to 'UVIR'
* The `azimuth` and `altitude` attributes hold the photometer current orientation, in degrees. Default azimuth is 0.0 and default altitude is 90.0

##### Version Control Attributes
These columns manage the version control of a given TESS attributes.
* Columns `valid_since` and `valid_until` hold the timestamps where the changes to version controlled attributes are valid. 
* Column `valid_state` is an indicator. Its values are either **`Current`** or **`Expired`**. 
The current valid TESS instrument has its `valid_state` set to `Current` and the expiration date in a far away future (Y2999).

#### Unit dimension

The `tess_units_t` table collects various flags for the fact table. 

* (OBSOLETE) Columns `valid_since`, `valid_until` and `valid_state` keep track of any units change in a similar technique as above should the units change.

#### Location dimension

This dimension table holds all known locations where TESS photometers are to be deployed.

* `site`. Unique site name describing the this location.
* `contact_person`. Person to account for observations.
* `organization`. Organization where the contact person belongs to or running the facilities in the location.
* `contact_email`. Contact person email address.
* `longitude` Location longitude in degrees. West is negative.
* `latitude`. Location latitude in degrees
* `elevation`. Location elevation in meters
* `zipcode`. Location ZIP code
* `province`. Location country
* `country`. Location country
* `timezone`. Time zone (to calculate local time) in standard format described by Wikipedia[https://en.wikipedia.org/wiki/List_of_tz_database_time_zones]
* `sunrise` & `sunset`. Computed attributes (oce per day) used to filter out readings in daylight.

### Fact Tables
They are:

* `tess_readings_t` : Accumulating snapshot fact table containing measurements from several TESS instruments.

TESS devices with accelerometer will send `azimuth` and `altitude` values, otherwise they are `NULL`.

TESS devices with a GPS will send `longitude`, `latitude` and `height` values, otherwise they are `NULL`.

### Other Tables

It is possible now to replace a given TESS-W and keep the name. This is sueful for sites that wish to announce a simbolic name for its TESS-W photometer and never change even if the device is replaced (i.e. by being broken).

So now, a given name ***does not*** identify a TESS-W photometer, only the MAC address does. An association table is needed

* `name_to_mac_t` : Association table to label a given TESS-W device (identified by its MAC address) to a symbolic name.


## Sample SQL Queries

The following are samples queries illustraing how to use the data model. They are actually being used by the STARS4ALL project

1. Get a daily report of readings per instrument:

```sh
#!/bin/bash
sqlite3 /var/dbase/tess.db <<EOF
.mode column
.headers on
SELECT d.sql_date, i.mac_address, count(*) AS readings
FROM tess_readings_t AS r
JOIN tess_t AS i USING (tess_id)
JOIN date_t AS d USING (date_id)
GROUP BY r.date_id, r.tess_id
ORDER BY d.sql_date DESC;
EOF
```

2. Extract a CSV (semicolon separated) with all readings for an instrument passed as a command line argument:

```sh
#!/bin/bash
instrument_name=$1
sqlite3 -csv -header /var/dbase/tess.db <<EOF
SELECT (d.julian_day + t.day_fraction) AS julian_day, (d.sql_date || 'T' || t.time) AS timestamp, r.sequence_number, l.site, i.mac_address, r.frequency, r.magnitude, i.zero_point, r.sky_temperature, r.ambient_temperature
FROM tess_readings_t AS r
JOIN tess_t          AS i USING (tess_id)
JOIN location_t      AS l USING (location_id)
JOIN date_t          AS d USING (date_id)
JOIN time_t          AS t USING (time_id)
WHERE i.mac_address  IN (SELECT mac_address FROM name_to_mac_t WHERE name = "${instrument_name}")
ORDER BY r.date_id ASC, r.time_id ASC;
EOF
```

3. Show current TESS instruments. Note that we are using the `tess_v` View,so that the current location info is already included.

```sh
#!/bin/bash
sqlite3 /var/dbase/tess.db <<EOF
.mode column
.headers on
SELECT v.name AS Name, v.mac_address AS MAC, (v.latitude || ' ' || v.longitude) AS Coordinates , (v.site || ', ' || v.location || ', ' || v.province) AS Location, v.contact_email as User, v.zero_point as ZP, v.filter as Filter
FROM tess_v AS v
WHERE v.valid_state = "Current"
ORDER BY v.name ASC;
EOF
```

4. Show TESS instruments changes (zero point and/or filter)

```sh
#!/bin/bash
sqlite3 /var/dbase/tess.db <<EOF
.mode column
.headers on;
SELECT i.name AS Name, i.zero_point as ZP, i.filter as Filter, i.valid_since AS Since, i.valid_until AS Until, i.valid_state AS 'Change State'
FROM tess_t AS i
ORDER BY i.name ASC, i.valid_since ASC;
EOF
```

5. Show the time span of readings per TESS
```sh
#!/bin/bash
sqlite3 /var/dbase/tess.db <<EOF
.mode column
.headers on;
SELECT i.mac_address, MIN(d.sql_date || 'T' || t.time || 'Z') AS earliest, MAX(d.sql_date || 'T' || t.time || 'Z') AS latest
FROM tess_readings_t AS r
JOIN tess_t          AS i USING (tess_id)
JOIN location_t      AS l USING (location_id)
JOIN date_t          AS d USING (date_id)
JOIN time_t          AS t USING (time_id)
GROUP BY i.mac_address;
EOF
```

6. Show locations not assigned to any TESS
```sh
#!/bin/bash
sqlite3 /var/dbase/tess.db <<EOF
.mode column
.headers on;
SELECT l.site
FROM location_t        AS l 
LEFT OUTER JOIN tess_t AS i USING (location_id)
WHERE i.mac_address IS NULL;
EOF
```

# MQTT PAYLOAD INFORMATION

Payloads are transmitted in JSON format, with the format described below.

## Published on  topic 'STARS4ALL/{channel}/reading'

| Field name |  Type  | Units | Optional | Description                       |
|:----------:|:------:|:-----:|:--------:|:----------------------------------|
| seq        | int    |   -   | mand  | Sequence number. If possible use 32 bits. The sequence number will start in 1 at each device reboot. |
| name       | string |   -   | mand  | Instrument friendly name. Should be unique as it identifies the device. |
| freq       | float  | Hz    | mand  | Raw reading as a frequency with 3 decimal digits precision (millihertz) NNNNN.NNN |
| mag        | float  | mag/arcsec^2 | mandat. | Visual magnitude (formulae?) corresponding to the raw reading). Transmitted up to two decimal places NN.NN |
| tamb       | float   | ºC    | mandat. | Ambient Temperature. Transmitted up to one decimal place. |
| tsky       | float   | ºC    | mandat.  | Sky Temperature. Transmitted up to one decimal place. |
| wdBm       | int     | dBm | opt | WiFi Received Signal Strength. |
| az         | int     | deg | opt | Photometer optical axis Azimuth sent only on instruments with accelerometer. |
| alt | int | deg | opt | Photometer optical axis Altitude (angle): sent only on instruments with accelerometer. |
| lat | float | deg | opt | Instrument latitude. Only sent by instruments with GPS integration. |
| long | float | deg | opt | Instrument longitude. Only sent by instruments with GPS integration. |
| height | float | meters | opt | Instrument height above the sea level. Only sent by instruments with GPS integration. |
| rev | int | - | mand | Payload data format revision number. Current version is 1. |
| tstamp | string | UTC | opt | Timestamp,“YYYY-MM-DDTHH:MM:SS” format. Must be UTC. |

## Published on  topic 'STARS4ALL/register'

| Field name |  Type  | Units | Optional | Description                       |
|:----------:|:------:|:-----:|:--------:|:----------------------------------|
| name  | string | - | mand | Instrument friendly name. Should be unique as it identifies the device. |
| mac   | string | - | mand. | Device MAC address, format “xx:yy:zz:rr:ss:tt” |
| calib | float  | mag/arcsec^2 | mand | Per-device Zero Point. Transmitted as NN.NN floating point. |
| rev   | int    | - | mand | Payload data format revision number. Current version is 1. |
| chan  | string | - | opt | Channel where this instrument will publish its readings. |


# OPERATION & MAINTENANCE

## Pause & resume

Since the current database used is SQLite - a single user database - you need to pause tessdb-server if dealing directly with the database
like issuing SQL commands directly or using the `tess` command line utility

Use `/usr/local/bin/tessdb_pause` and `/usr/local/bin/tessdb_resume` to coordinate your direct interactions to the database with tessdb-server.

## Reload

Since tessdb-server maintains a RAM cache of photometers data, some `tess` command requires a server reload to rfefress the cache.
The `tess`utility wanrs you when this is necessary.

## Restart

The newest filter operation mode in tessdb-server maintains a sliding window of photometers samples before writting to database
If it is necessary to restart the server, use `/usr/local/bin/tessdb_restart` instead of `service tessdb restart`. This will ensure that the lastest
readings are stored in the database.

## The `tess` utility

`tess` is a command line utility to perform some common operations on the database without having to write SQL statements. As this utility modifies the database, it is necessary to invoke it within using `sudo`. Also, you should ensure that the database is not being written by `tessdb` to avoid *database is locked* exceptions, either by using it at daytime or by pausing the `tessdb` service with `/usr/local/bin/tessdb_pause` and then resume it with `/usr/local/bin/tessdb_resume`.
