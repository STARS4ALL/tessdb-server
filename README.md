# tessdb

Linux service to collect measurements pubished by TESS Sky Quality Meter via MQTT.
TESS stands for [Cristobal Garcia's Telescope Encoder and Sky Sensor](http://www.observatorioremoto.com/TESS.pdf)

## Description

**tessdb** is a software package that collects measurements from one or several
TESS instruments into a SQLite Database. 

Desktop applicatons may query the database to generate reports and graphs
using the accumulated, historic data.

These data sources are available:

+ individual samples (real time, 5 min. aprox between samples).

The sampling period should be > 1 min.

**Warning**: Time is UTC, not local time.

## Installation & Configuration

See the [INSTALL.md file](INSTALL.md)

## Operation & Mainenance

See the [MAINTENANCE.md file](MAINTENANCE.md)

## Data Model

See the [DATABASE.md file](DATABASE.md)

