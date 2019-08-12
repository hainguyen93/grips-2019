# Timetable extractor from the input dateset (in xml format)
# @author: Hai Nguyen

import xml.etree.ElementTree as ET
import datetime
import sys, os
import time

from dateutil.parser import parse
from datetime import datetime, timedelta
from exceptions import *

DAYS = [ "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" ]

FOLLOWING_DAY =  dict(zip(DAYS, DAYS[1:]+DAYS[:1]))


def create_driving_edges(xml_root, day, driving_edges):
    """ Generating all driving edges for the selected day

    Attributes:
        xml_root        : root of the xml tree
        day             : a specific day of the week (Mon, Tue,...)
        driving_edges   : list of driving edges
        ice :  ice fleet
    """
    for train in xml_root.iter('Train'):
        train_id = int(train.get('TrainID_'))

        for trip in train.iter('Trip'):
            trip_validity = trip.find('Validity').get('BitString')

            if trip_validity[DAYS.index(day)] is not '1':
                continue

            is_next_day = False # overnight or not?

            stop_list = list(trip.iter('Stop'))

            for i in range(1, len(stop_list)):

                from_station = stop_list[i-1].get('StationID').replace(" ", "")
                departure_time = stop_list[i-1].get('DepartureTime')

                to_station = stop_list[i].get('StationID').replace(" ", "")
                arrival_time = stop_list[i].get('ArrivalTime')

                passenger_number = int(stop_list[i-1].get('Passagiere'))

                if departure_time > arrival_time: # overnight
                    is_next_day = True
                    departure_time = day + departure_time
                    arrival_time = FOLLOWING_DAY[day] + arrival_time
                elif not is_next_day:
                    departure_time = day + departure_time
                    arrival_time = day + arrival_time
                elif is_next_day:
                    departure_time = FOLLOWING_DAY[day] + departure_time
                    arrival_time = FOLLOWING_DAY[day] + arrival_time

                # calculating the travelling time (in minutes)
                travel_time_seconds = (parse(arrival_time)-parse(departure_time)).seconds
                travel_time_minutes = (travel_time_seconds % 3600) // 60

                new_edge = tuple((from_station, departure_time, to_station, arrival_time, passenger_number, travel_time_minutes))
                driving_edges.append(new_edge)


def create_list_of_events(driving_edges, events):
    """ Create list of events

    Attributes:
        driving_edges   : list of driving edges
        events          : dictionary with stations as keys and list of timestamps as values
    """
    for edge in driving_edges:
        for indx in [0,2]:
            station = edge[indx]
            if edge[indx] in events:
                events[station].append(edge[indx+1])
            else:
                events[station] = [edge[indx+1]]

    for station in events:
        unduplicate_timestamps = list(set(events[station]))
        events[station] = sorted(unduplicate_timestamps, key=timestamp_to_seconds)



def timestamp_to_seconds(timestamp):
    """Convert timestamp into seconds"""
    return time.mktime(parse(timestamp).timetuple())



def create_waiting_edges(waiting_edges, events):
    """ Create all waiting edges for a day

    Attributes:
        waiting_edges   : list of waiting edges
        events          : dictionary of stations and list of timestamps
    """
    for station, timestamps in events.items():
        for i in range(len(timestamps)-1):
            travel_time_seconds = (parse(timestamps[i+1])-parse(timestamps[i])).seconds
            travel_time_minutes = (travel_time_seconds % 3600) // 60
            new_edge = tuple((station, timestamps[i], station, timestamps[i+1], 0, travel_time_minutes))
            waiting_edges.add(new_edge)


def extract_edges_from_timetable(timetable, chosen_day):
    """Create list of driving and waiting arcs from the xml timetable file
    to construct the time-extended graph
    
    Attributes:
        timetable : the xml timetable file 
        chosen_day : day chosen to produce inspection shedule (e.g., Mon, Tue, etc)
        
    Return a list of 6-tuples 
        (from_station, departure_time, to_station, arrival_time, passenger_number, travel_time)
    """  
    try: 
        print('Extracting waiting and driving arcs from timetable...', end=' ')
    
        driving_edges = list()
        waiting_edges = set() # to avoid duplicate

        # dictionary with station as keys and list of timestamps as values
        events = dict()

        tree = ET.parse(timetable)
        root = tree.getroot()

        create_driving_edges(root, chosen_day, driving_edges)
        create_list_of_events(driving_edges, events)
        create_waiting_edges(waiting_edges, events)
    
        print('{} driving arcs and {} waiting arcs'.format(len(driving_edges), len(waiting_edges)))
        return driving_edges + list(waiting_edges)
    
    except ET.ParseError as error:
        print(error)
        sys.exit(1)
        
        
