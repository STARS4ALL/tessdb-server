# C. OPERATION & MAINTENANCE


## C.1 Server Start/Stop/Restart

### C.1.1 Linux

* Service status: `sudo service emadb status`
* Start Service:  `sudo service emadb start`
* Stop Service:   `sudo service emadb stop`
* Restart Service: `sudo service emadb restart`. A service restart kills the process and then starts a new one

    sudo service emadb reload

### C.2.2 Windows

The start/stop/restart/pause operations can be performed with the Windows service GUI tool
**If the config.ini file is not located in the usual locatioon, you must supply its path to the tool as extra arguments**

From the command line:

* Start Service:  Click on the `start_service.bat` file
* Stop Service:   Click on the `stop_service.bat` file
* Restart Service: `????`. A server restart kills the process and then starts a new one

## C.2 Server Pause

The server can be put in *pause mode*, in which will be still receiving incoming MQTT messages but will be internally enquued and not written to the database. This is usefull to perform delicate operations on the database without loss of data. Examples:

* Compact the database usoing the SQLite VACUUM pragma
* Migrating data from tables.
* etc.

### C.2.1 Linux

To pause the server, type: `sudo service emadb pause` and watch the log file output wit `tail -f /var/log/emadb.log`

To resume normal operation type again the same command and observe the same log file.

### C.2.2 Windows

## C.3 Service reload

During a reloadn the service is not stopped and re-reads the new values form the configuration file and apply the changes. In general, all aspects not related to maintaining the current connection to the MQTT broker can be relaoded. The full list is sescribed in the section B above.

* *Linux:* The `service emadb reload` will keep the MQTT connection intact. 
* *Windows:* There is no GUI button in the service tool for a reload. You must execute an auxiliar script `C:\emadb\scripts\winreload.py` by double-clicking on it. 

In both cases, watch the log file to ensure this is done.

  
## C SQLite Database Maintenance

### C.1. Reloadable Parameters

TBD (if ever supported by Twisted)

### C.2 Updating the registered stations list

**tessdb will only insert incoming MQTT data if the TESS instrument is previously registered in the database**. While you can update the database itself using SQL commands, the preferred approach is to edit the master dimension JSON files, usually stored in the `/etc/tessdb` directory (Linux) or `C:\tessdb\config.ini` (Windows).

Edit the files using your favorite editor. Beware, JSON is picky with the syntax.

* To **append** new data in these files, simply reload or restart the service.
* To **modify** existing data (i.e. changing existing instrument data), use the tessdb_update utility.

	* *Linux:* Type `sudo tessdb_update -h` to see the command line arguments.
	* *Windows:* Double-click to execute on the `C:\emadb\scripts\winreload.py` file







