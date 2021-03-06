#!/usr/bin/env python2

# PTV DB to GTFS converter for Victorian Public Transport
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sqlite3
import re
import datetime
from optparse import OptionParser

import transitfeed

SETTINGS = {
    'train': {
        'file': 'Metlink-Train.sql',
        'name': 'Metro Trains',
        'prefix': 'train',
        'system': 'Subway',
        'state': 'VIC',
    },
    'tram': {
        'file': 'Metlink-Tram.sql',
        'name': 'Yarra Trams',
        'prefix': 'tram',
        'system': 'Tram',
        'state': 'VIC',
    },
    'bus': {
        'file': 'Metlink-Bus.sql',
        'name': 'Melbourne Bus',
        'prefix': 'bus',
        'system': 'Bus',
        'state': 'VIC',
    },
    'vline': {
        'file': 'Metlink-VLine.sql',
        'name': 'V/Line',
        'prefix': 'vline',
        'system': 'regional',
        'state': 'VIC',
    }
}

def process_routes(cur, config, schedule):
    # Routes
    print "..processing routes.."
    cur.execute("select * from " + config['prefix'] + "_lines")
    for row in cur:

        # Start with a sensible default of using the route_long_name.
        # You don't want to wait hours and hours to find out that
        # neither route_long_name or route_short_name has been set.
        route_long_name = row["line_name"].strip()
        route_short_name = None
        route_description = None

        # Train
        if config['system'] == 'Subway':
            route_long_name = row['line_name'].strip()
            route_type = config['system']

        # Tram
        elif config['system'] == 'Tram':
            # 1 - East Coburb - South Melbourne
            temp_name = row['line_name'].split(' - ')
            route_short_name = temp_name[0]
            route_long_name = temp_name[1]
            if len(temp_name) == 3:
                route_long_name = '%s to %s' % (route_long_name, temp_name[2])

        # V/Line
        elif config['system'] == 'V/Line':
            # Echuca-Moama - Melbourne via Shepparton
            m = re.match('(.*\s-\s.*) via (.*)', row["line_name"].strip())            
            if m:
                short_name = m.groups()[0].replace(" - ", " to ")
                route_name = '%s Line' % short_name
                long_name = m.group(0).replace(" - ", " to ")

        # Bus
        elif config['system'] == 'Bus':
            # 123 - Here - There
            # 843-845-849-861 - Dandenong - Endeavour Hills via Doveton
            m = re.match('([\d{3}?-]+) - (.*)', row["line_name"].strip())
            if m:
                route_short_name = m.groups()[0]
                route_long_name = m.groups()[1]
            else:
                m = re.match('(.*) \(Routes? (.*)\)', row["line_name"].strip())
                if m:
                    route_short_name = m.groups()[1]
                    route_long_name = m.groups()[0]
                else:
                    
                    m = re.match('(.*) combined - (.*)', row["line_name"].strip())
                    if m:
                        route_short_name = m.groups()[0]
                        route_long_name = m.groups()[1]
                    else:
                        # Geelong City - Newtown via Aberdeen St (Anticlockwise Circular - Route 36)
                        m = re.match('.* - Route (.*)\)', row["line_name"].strip())
                        if m:
                            route_short_name = m.groups()[0]
                            route_long_name = row["line_name"].strip()

        route_id = str(row['line_id'])

        # Add our route
        route = transitfeed.Route(
            short_name = route_short_name, 
            long_name = route_long_name,
            route_type = config['system'],
            route_id = route_id
        )

        schedule.AddRouteObject(route)
    print "..done processing routes."

    

def process_stops(cur, config, schedule):
    print "..processing stops.."
    # Stops
    cur.execute("select * from "+ config['prefix'] + "_locations")
    for row in cur:

        stop_name = None
        stop_desc = None
        stop_code = None

        # Train
        if config['system'] == 'Subway':
            # Custom name for train stations
            stop_name = '%s Station' % row['location_name'].strip()

        elif config['system'] == 'Tram':
            # Custom name for tram
            # Match both:
            m = re.match('(.*)\s#(\d+)', row['location_name'].strip())
            # Street Name/Other Street #123
            if m:
                stop_code = m.groups()[1]
                stop_name = m.groups()[0]
            else:
                # 7D-Street Name/Other Street
                m = re.match('(\w+)-(.*)', row["location_name"].strip())
                try:
                    stop_code = m.groups()[0]
                    stop_name = m.groups()[1]
                except:
                    print ("Warning: tram stop entry in DB "\
                        "seems to be missing stop code:- entering "\
                        "with name as '%s'" % row["location_name"].strip())
                    stop_name = row['location_name'].strip()

        else:
            stop_name = row['location_name'].strip()

        stop_id = str(row['location_id'])
        lat = row["latitude"]
        lng = row["longitude"]

        stop = transitfeed.Stop(
            stop_id = stop_id,
            name = stop_name,
            stop_code = stop_code,
            lat = lat,
            lng = lng,
        )

        schedule.AddStopObject(stop)
    print "..done processing stops."

def process_stoptimes(cur, config, schedule):
    print "..processing stoptimes.."

    timetables = []

    # Lookup which times we have
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '" + config['prefix'] + "_stops%' ORDER BY name;")
    for row in cur:
        # Table name is train_stops_monthur, so get the last part
        name = row['name'].split('_')[-1]
        timetables.append(name)

    for timetable in timetables:

        print("Processing timetable: %s" % timetable)
        service_period = transitfeed.ServicePeriod(id=timetable)
        # TODO: Don't hardcode these dates
        service_period.SetStartDate('20140101')
        service_period.SetEndDate('20141231')

        # Set the day of week times
        if timetable == 'monthur':
            service_period.SetDayOfWeekHasService(0)
            service_period.SetDayOfWeekHasService(1)
            service_period.SetDayOfWeekHasService(2)
            service_period.SetDayOfWeekHasService(3)
        elif timetable == 'fri':    
            service_period.SetDayOfWeekHasService(4)
        elif timetable == 'monfri':
            service_period.SetWeekdayService()
        elif timetable == 'sat':
            service_period.SetDayOfWeekHasService(5)
        elif timetable == 'sun':
            service_period.SetDayOfWeekHasService(6)
        else:
            print("Error: Timetable %s not defined" % timetable)

        schedule.AddServicePeriodObject(service_period, validate=False)
        process_stoptime(cur, config, schedule, service_period, timetable)
    print "..done processing stoptimes."

PROGRESS_INCS = 20

def process_stoptime(cur, config, schedule, service_period, table):
    
    # Lookup our directions first
    directions = {}
    cur.execute("select * from "+ config['prefix'] + "_direction")
    for row in cur:
        direction_id = row["direction_id"]
        name = row['direction_name']
        directions[direction_id] = name

    # Save these for helping us work out services that run past midnight
    last_trip_id = 0
    last_time = 0

    print "..Getting stops database entries.."
    cur.execute("select * from "+ config['prefix'] + "_stops_" + table)
    rows = cur.fetchall()
    num_stop_times = len(rows)
    print "..got %d stop times database entries.." % num_stop_times
    inc_divisor = num_stop_times / float(PROGRESS_INCS)
    next_inc_period = 1

    print "..starting processing each stop time entry.."
    for ii, row in enumerate(rows):
        route_id = str(row['line_id'])
        stop_id = str(row['stop_id'])
        trip_id = str(row['run_id'])
        headsign = directions[int(row["direction"])] # Get the direction from the other table
        time = row["time"]
        # Now use of Get() API of transitfeed to save search time.
        route = schedule.GetRoute(route_id)
        stop = schedule.GetStop(stop_id)

        # If the next time is past midnight, add more time to take it past 24 hours,
        # because GTFS requires it
        if time < last_time:
            if last_trip_id == trip_id:
                time += 86400
        last_time = time
        last_trip_id = trip_id

        try:
            trip = schedule.GetTrip(trip_id)
        except KeyError:    
            # If we don't have an existing trip, create a new one and add
            trip = route.AddTrip(
                schedule, 
                headsign = headsign,
                trip_id = trip_id,
                service_period = service_period 
            )

        # We know the stops times are in row order, so we'll
        # just make up the sequence here
        stop_seq = trip.GetCountStopTimes()

        # Not sure what we should do about this
        problems = None

        stop_time = transitfeed.StopTime(
            problems, 
            stop,
            pickup_type = 0, # Regularly scheduled pickup 
            drop_off_type = 0, # Regularly scheduled drop off
            shape_dist_traveled = None, 
            arrival_secs = time,
            departure_secs = time, 
            stop_time = time, 
            stop_sequence = stop_seq
        )

        trip.AddStopTimeObject(stop_time)
        if (ii+1) / inc_divisor > next_inc_period:
            print "....processed %d stops (%.1f%% of total).." % \
                (ii+1, next_inc_period/float(PROGRESS_INCS)*100)
            next_inc_period += 1

    print "..done processing each stop time entry.."


def process_data(inputdb, config, output):

    # Open SqliteDB
    con = sqlite3.connect(inputdb)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    # Create our schedule
    schedule = transitfeed.Schedule()

    # Agency
    schedule.AddAgency(config['name'], "http://ptv.vic.gov.au", "Australia/Melbourne")

    process_routes(cur, config, schedule)
    process_stops(cur, config, schedule)
    process_stoptimes(cur, config, schedule)

    accumulator = transitfeed.SimpleProblemAccumulator()
    problemReporter = transitfeed.ProblemReporter(accumulator)
    print "Validating result..."
    schedule.Validate(problems=problemReporter)
    print "...done."
    print "Writing to file %s ..." % output
    schedule.WriteGoogleTransitFeed(output)
    print "...done."

if __name__ == "__main__":

    usage = "usage: %prog --file <input db> --service <service> --output <output file>"
    parser = OptionParser(usage)
    parser.add_option('-f', '--file', 
        dest='inputdb', 
        help='PTV SQLite3 database file.')

    parser.add_option('-s', '--service', 
        dest='service',
        help='Should be train, tram or bus.')

    parser.add_option('-o', '--output',
        dest='output',
        help='Path of output file. Should end in .zip')

    (options, args) = parser.parse_args()

    if not options.inputdb:
        parser.error("You must supply the input database filename.")

    if not options.service:
        parser.error("You must supply the service type (e.g. train, tram, bus).")

    if not options.output:
        parser.error("You must supply the output filename.")

    config = SETTINGS[options.service]
    process_data(options.inputdb, config, options.output)
