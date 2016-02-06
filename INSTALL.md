# A. INSTALLATION

## A.1. Requirements

The following components should be installed first:

The following components are needed:

 * python 2.7.x (tested on Ubunti python 2.7.6 & Windows XP python 2.7.10)

The Windows python 2.7 distro comes with the pip utility included. 
    
## A.2 Linux installation (Debian)

### A.2.1 Installation

Installation via PyPi repository

  `sudo pip install tessdb`

or from GitHub:

    git clone https://github.com/astrorafael/tessdb.git
    cd tessdb
    sudo python setup.py install


* All executables are copied to `/usr/local/bin`
* The database is located at `/etc/dbase/tessdb.db` by default
* The log file is located at `/var/log/tessdb.log`

### A.2.2 Start up Verification

Type `sudo tessdb` to start the service in foreground with console output.

Type `sudo service tessdb start` to start it as a backgroud service.
Type `sudo update-rc.d tessdb defaults` to start it at boot time.

## A.3. Windows installation

### A.3.1 Installation

1. Open a `CMD.exe` console, **with Administrator privileges for Windows 7 and higher**
2. Inside this new created folder type:

 `pip install tessdb`

* The executables (.bat files) are located in the same folder `C:\tessdb`
* The database is located at `C:\emadb\dbase` by default. It is strongly recommeded that you leave it there.
* The log file is located at `C:\emadb\log\emadb.log`

### A.3.2 Start up and Verification

In the same CMD console, type`.\tess.bat`to start it in forground and verify that it works.

Go to the Services Utility and start TESSDB database service.

# B. CONFIGURATION

There is a small configuration file for this service:

* `/etc/tessdb/config` (Linux)
* `/etc/tessdb/config.ini` (Windows)

This file is self explanatory. 
In special, the database file name and location is specified in this file.

### B.2. Logging

Log file is usually placed under `/var/log/tessdb.log` in Linux or `C:\tessdb\log` on Windows. 
Default log level is `INFO`. It generates very litte logging at this level.
File is rotated by the application itself. 
