# XML PARSER FOR THE INPUT DATE
# @AUTHOR(s): HAI

import xml.etree.ElementTree as ET
import datetime
import sys, os

from dateutil.parser import parse
from datetime import datetime, timedelta

# GLOBAL CONFIGURATIONS
USERNAME = 'bzfnguye'

ICE_NAMES = [ "401", "402", "403", "411" ]

DAY_DICT = { "Mon" : 0, 
            "Tue" : 1, 
            "Wed" : 2, 
            "Thu" : 3, 
            "Fri" : 4, 
            "Sat" : 5, 
            "Sun" : 6  }


def create_driving_edges(xml_root, day, driving_edges):
    """ Generating all driving edges for the selected day
    
    Attributes:        
        xml_root        : root of the xml tree
        day             : a specific day of the week (Mon, Tue,...) 
        driving_edges   : list of driving edges
    """   
    for train in xml_root.iter('Train'):
        train_id = train.get('TrainID_')
        
        for trip in train.iter('Trip'):
            trip_validity = trip.find('Validity').get('BitString')
            
            if trip_validity[DAY_DICT[day]] is not "1":
                continue
            
            stop_list = list(trip.iter('Stop'))
            stop_number = len(stop_list)
            
            for i in range(1, stop_number): 
                from_station = stop_list[i-1].get('StationID')
                departure_time = stop_list[i-1].get('DepartureTime')
                to_station = stop_list[i].get('StationID')
                arrival_time = stop_list[i].get('ArrivalTime')           		
                passenger_number = stop_list[i-1].get('Passagiere')
                
                # calculating the travelling time (i.e., datetime.timedelta objects)
                travel_time_seconds = (parse(arrival_time)-parse(departure_time)).seconds
                travel_time_minutes = (travel_time_seconds % 3600) // 60                    
                new_edge = tuple((from_station, departure_time, to_station, arrival_time, passenger_number, travel_time_minutes))
                driving_edges.append(new_edge)
                print(new_edge)

    

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
        events[station] = sorted(unduplicate_timestamps)     
        
                
                
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
            waiting_edges.append(new_edge)    
            print(new_edge)
            

                
def main():
    """ Main function 
    """   
    
    # List of 5-tuples 
    # E.G., (from_station, departure_time, to_station, arrival_time, passenger_number)
    driving_edges = list()
    waiting_edges = list()
        
    # dictionary with station as keys and list of timestamps as values
    events = dict()
        
    for ice in ICE_NAMES: 
        input_dir = "/home/optimi/" + USERNAME +"/inputData/EN_GRIPS2019_" + ice + ".xml"
        tree = ET.parse(input_dir)
        root = tree.getroot()
        create_driving_edges(root, "Mon", driving_edges)
        create_list_of_events(driving_edges, events)
        create_waiting_edges(waiting_edges, events)
            
    #number_of_edges = len(driving_edges)+len(waiting_edges)
    #number_of_nodes = sum([len(timestamps) for _, timestamps in events.items()])
        
    #print("{}: Edges: {} Nodes: {}".format(day, number_of_edges, number_of_nodes))
    with open("monday_arcs.txt", "w+") as file:
        for edge in driving_edges:
            file.write(" ".join(str(i) for i in edge) + "\n")
        for edge in waiting_edges:
            file.write(" ".join(str(i) for i in edge) + "\n")
           
                        
if __name__ == "__main__":
    main()
                        
                        
                        
                        
