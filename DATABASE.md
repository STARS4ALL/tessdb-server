# A. DATA MODEL

## A.1. Dimensional Modelling

The data model follows the [dimensional modelling approach by Ralph Kimball]
(https://en.wikipedia.org/wiki/Dimensional_modeling). More references can also be found in
[Star Schemas](https://en.wikipedia.org/wiki/Star_schema).

## A.2 The data model

The figure below shows the layout of **tessdb**.

![TESS Database Model](doc/tessdb-full.png)

### Dimension Tables

* `date_t`      : preloaded from 2016 to 2026
* `time_t`      : preloaded, with minute resolution
* `instrument_t`: registered TESS instruments collecting data
* `location_t`  : locations where instruments are deployed
* `units_t`     : an assorted collection of unit labels for reports, preloaded with current units.

#### Instrument Dimension

This dimension holds the current list of instruments. 
The real key is an artificial key `instrument_id` linked to the Fact table.
The `mac_address` is the natural key.
The `name` attribute is an alternative key. An instrument name can be changed
as log as there is no other instrument with the same name.
The `current_loc_id` is a reference to the current location assigned to the instrument.
Location id -1 denotes the "Unknown" location.
The `calibration_k` holds the current value of the instrument calibration constant.
A history of calibration constant changes are maintained in the `instrument_t` table
if the instrument is ever recalibrated. Columns `calibrated_since` and `calibrated_until`
hold the timestamps where the calibration constant is valid. Column `calibrated_state`
is an indicator. Its values are either **`Current`** or **`Expired`**. The current calibration
constant has its indicator set to `Current` and the expiration date in a far away future (Y2999).

#### Unit dimension

The `units_t` table is what Dr. Kimball denotes as a *junk dimension*. It collects ar labels denoting
the current measurement units of samples in the fact table. Should the units change, we keep track of them
in a similar technique as described in the `instrument_t` table. Columns `valid_since`, `valid_until` and
`valid_state` keep track of units change in a similar way as above.

### Fact Tables

* `readings_t` : Accumulating snapshot fact table containing measurements from several TESS instruents.

TESS devices with accelerometer will send `azimuth` and `altitude` values, otherwise they are `NULL`.
TESS devices with a GPS will send `longitude`, `latitude` and `height` values, otherwise they are `NULL`.

## A.3 Sample queries

TBD

## A.4 data mode listing

      ```
            CREATE TABLE IF NOT EXISTS date_t
            (
            date_id        INTEGER PRIMARY KEY, 
            sql_date       TEXT, 
            date           TEXT,
            day            INTEGER,
            day_year       INTEGER,
            julian_day     REAL,
            weekday        TEXT,
            weekday_abbr   TEXT,
            weekday_num    INTEGER,
            month_num      INTEGER,
            month          TEXT,
            month_abbr     TEXT,
            year           INTEGER
            );

            CREATE TABLE IF NOT EXISTS time_t
            (
            time_id        INTEGER PRIMARY KEY, 
            time           TEXT,
            hour           INTEGER,
            minute         INTEGER,
            day_fraction   REAL
            );

            CREATE TABLE IF NOT EXISTS units_t
            (
            units_id                  INTEGER PRIMARY KEY AUTOINCREMENT, 
            frequency_units           REAL,
            magnitude_units           REAL,
            ambient_temperature_units REAL,
            sky_temperature_units     REAL,
            azimuth_units             REAL,
            altitude_units            REAL,
            longitude_units           REAL,
            latitude_units            REAL,
            height_units              REAL,
            valid_since               TEXT,
            valid_until               TEXT,
            valid_state               TEXT
            );

            CREATE TABLE IF NOT EXISTS location_t
            (
            location_id             INTEGER PRIMARY KEY,
            contact_email           TEXT,
            site                    TEXT,
            zipcode                 TEXT,
            location                TEXT,
            province                TEXT,
            country                 TEXT
            );

            CREATE TABLE IF NOT EXISTS instrument_t
            (
            instrument_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT,
            mac_address        TEXT, 
            calibration_k      REAL,
            calibrated_since   TEXT,
            calibrated_until   TEXT,
            calibrated_state   TEXT,
            current_loc_id     INTEGER NOT NULL DEFAULT -1 REFERENCES location_t(location_id)
            );

            CREATE TABLE IF NOT EXISTS readings_t
            (
            date_id             INTEGER NOT NULL REFERENCES date_t(date_id), 
            time_id             INTEGER NOT NULL REFERENCES time_t(time_id), 
            instrument_id       INTEGER NOT NULL REFERENCES instrument_t(instrument_id),
            location_id         INTEGER NOT NULL REFERENCES location_t(location_id),
            units_id            INTEGER NOT NULL REFERENCES units_t(units_id),
            sequence_number     INTEGER,
            frequency           REAL,
            magnitude           REAL,
            ambient_temperature REAL,
            sky_temperature     REAL,
            azimuth             REAL,
            altitude            REAL,
            longitude           REAL,
            latitude            REAL,
            height              REAL,
            timestamp           TEXT,
            PRIMARY KEY (date_id, time_id, instrument_id)
            );
      ```