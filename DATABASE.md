# A. DATA MODEL

## A.1. Dimensional Modelling

The data model follows the [dimensional modelling]
(https://en.wikipedia.org/wiki/Dimensional_modeling) approach by Ralph Kimball. 
More references can also be found in [Star Schemas](https://en.wikipedia.org/wiki/Star_schema).

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

The `units_t` table is what Dr. Kimball denotes as a *junk dimension*. It collects various labels denoting
the current measurement units of samples in the fact table. Columns `valid_since`, `valid_until` and
`valid_state` keep track of units change in a similar technique as above should the units change.

### Fact Tables

* `readings_t` : Accumulating snapshot fact table containing measurements from several TESS instruents.

TESS devices with accelerometer will send `azimuth` and `altitude` values, otherwise they are `NULL`.
TESS devices with a GPS will send `longitude`, `latitude` and `height` values, otherwise they are `NULL`.

## A.3 Sample queries

TBD

