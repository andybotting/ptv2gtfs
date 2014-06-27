ptv2gtfs
========

This is a conversion script to translate from the standard Metlink/PTV SQLite3
timetable database format used by PTV applications (e.g. iPhone app) to GTFS.


Requirements
------------

   * Python v2.7
   * [Google Transitfeed] [transitfeed]
   * A MetLink/PTV database (SQLite3 DB)

This has only been tested on Linux and Mac OS X using Python 2.7. 
It should probably work on any platform.

Obtaining the data
------------------

Currently, obtaining and using this database is up to you, and may or may not
be legal. I believe the Department of Transport may not like it.

You may be better off to use the [PTV Timetable API] [timetable_api].

Usage
-----

Command line help looks like this:

```
Usage: ptv2gtfs.py --file <input db> --service <service> --output <output file>

Options:
  -h, --help                     show this help message and exit
  -f INPUTDB, --file=INPUTDB     PTV SQLite3 database file
  -s SERVICE, --service=SERVICE  Should be train, tram or bus
  -o OUTPUT, --output=OUTPUT     Path of output file (should end in .zip)
```

An example of the output used for tram timetable data looks like this:

```
$ ./ptv2gtfs.py --file Metlink-Tram.sql --service tram --output tram_gtfs.zip
Processing timetable: fri
Processing timetable: monfri
Processing timetable: monthur
Processing timetable: sat
Processing timetable: sun
All services are defined on a weekly basis from 2014-01-01 to 2014-12-31 with
no single day variations. If there are exceptions such as holiday service
dates please ensure they are listed in calendar_dates.txt
The stops "Batmans Hill Dr/Collins St" (ID 2701) and "Batman's Hill/700
Collins St" (ID 2489) are 0.00m apart and probably represent the same
location.
The stops "Cotham Rd/Burke Rd" (ID 2695) and "1219 Burke Rd" (ID 2436) are
0.00m apart and probably represent the same location.
```

The output zip file (tram_gtfs.zip) in this case is our resulting GTFS data
file.

Performance: This script can take up to 10 minutes to run on a large DB, such
as Victoria's bus network.
It will also require over 100MB of RAM (e.g., between 800MB - 1GB for the bus
network).

Once the data has been processed, you can use the schedule_viewer.py script
provided with Google's Transitfeed package to visualise the data:

```
$ schedule_viewer.py train_gtfs.zip
Loading data from feed "train_gtfs.zip"...
(this may take a few minutes for larger cities)
routes.txt:1 column route_short_name
Missing column route_short_name in file routes.txt
To view, point your browser at http://localhost:8765/
```

Limitations
------------

Currently this script does NOT deal with special timetable days, like public
holidays.

You may also find inconsistancies within the data provided. This is up to you
to resolve.

Contact
-------

Feel free to contact me at andy@andybotting.com for any questions. 

If you find this useful, please let me know. Pull requests appreciated.

[timetable_api]: https://www.data.vic.gov.au/raw_data/ptv-timetable-api/6056
[transitfeed]: http://code.google.com/p/googletransitdatafeed
