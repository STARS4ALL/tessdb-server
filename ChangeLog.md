# Change Log
# 4.0.0
Datamodel revision to include TESS4C
Buffered database write.
# 3.0.0
Server changes to exception code.
Source code refactoring, simplification and new packaging scheme (pyproject.toml)
# 2.6.0
First release as a standalone tessdb-server package. Production-ready

# 2.0.0
standalone systemd service along with dbase backup by logrotate and pause/resume scripts
# 1.1.4
* Latest release with all the report scripts and tess utility bundled with the tessdb service
#| 1.0.5
* Added `tess instrument history` command to tess utility

#| 1.0.4
* Added `tess location create` command to tess utility
* Added `tess location update` command to tess utility

## 1.0.3

* changed filter column default vaue from `DG` to `UVIR`
* Updated README.md.

## 1.0.2

* fixed --log option to `tess instrument list` command line utility

## 1.0.1

* Doc fixes.
* Added context (row info) to logfile in SQL Exception when writting samples.
* Added various options to `tess` command line utility.

## 1.0.0

* Renaming columns for zero point and dates in `tess_t` table
* Added a `filter` column in `tess_t` table to manage filters
* Changed `tess` command line utility to manage TESS filters

## 0.x.y

Eariler prototype versions.

