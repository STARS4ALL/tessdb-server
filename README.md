# tessdb (overview)

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

## Operation & Mainenance

See the [MAINTENANCE.md file](MAINTENANCE.md)

## Data Model

See the [DATABASE.md file](DATABASE.md)

# INSTALLATION

## Requirements

The following components should be installed first:

The following components are needed:

 * python 2.7.x (tested on Ubunti python 2.7.6 & Windows XP python 2.7.10)

The Windows python 2.7 distro comes with the pip utility included. 
    
## Linux installation (Debian)

### Installation

Installation via PyPi repository

  `sudo pip install tessdb`

or from GitHub:

    git clone https://github.com/astrorafael/tessdb.git
    cd tessdb
    sudo python setup.py install


* All executables are copied to `/usr/local/bin`
* The database is located at `/var/dbase/tess.db` by default
* The log file is located at `/var/log/tessdb.log`

### Start up Verification

Type `sudo tessdb -k` to start the service in foreground with console output.

Type `sudo service tessdb start` to start it as a backgroud service.
Type `sudo update-rc.d tessdb defaults` to start it at boot time.

## Windows installation

## Pregrequisites

* Have Python 2.7 for Windows installed.
* Have the [Microsoft Visual C++ Compiler for Python 2.7](https://www.microsoft.com/en-us/download/details.aspx?id=44266) installed.
Systems requirements state for Windows 7+, but it works fine for Windows XP, 32bits. 

### Installation

1. Open a `CMD.exe` console, **with Administrator privileges for Windows 7 and higher**
2. Inside this console type:

`pip install twisted`

Twisted will install (15.5.0 at this moment)

You can test that this installation went fine by opening a python command line (IDLE or Python CMD)
and type:

	```
	>>> import twisted
	>>> print twisted.__version__
	15.5.0
	>>> _
	```

3. Inside this new created folder type:

 `pip install tessdb`

* The executables (.bat files) are located in the same folder `C:\tessdb`
* The database is located at `C:\emadb\dbase` by default. It is strongly recommeded that you leave it there.
* The log file is located at `C:\emadb\log\emadb.log`

### Start up and Verification

In the same CMD console, type`.\tess.bat`to start it in forground and verify that it works.

Go to the Services Utility and start TESSDB database service.

# CONFIGURATION

There is a small configuration file for this service:

* `/etc/tessdb/config` (Linux)
* `/etc/tessdb/config.ini` (Windows)

This file is self explanatory. 
In special, the database file name and location is specified in this file.

###Logging

Log file is usually placed under `/var/log/tessdb.log` in Linux or under `C:\tessdb\log` folder on Windows. 
Default log level is `info`. It generates very litte logging at this level.
File is rotated by logrotate under Linux. 
For Windows, it requires support from an exteral log rotator software such as [LogRotateWin](http://sourceforge.net/projects/logrotatewin/)

