# XML PARSER FOR THE INPUT DATE
# @AUTHOR(s): HAI

import xml.etree.ElementTree as ET
import datetime
import sys, os

# GLOBAL CONFIGURATIONS
USERNAME = 'bzfnguye'

ICE_NAMES = [ "401", "402", "403", "411" ]

# Map a day to a number from 0 to 6
day_dict = { "Mon" : 0, 
             "Tue" : 1, 
             "Wed" : 2, 
             "Thu" : 3, 
             "Fri" : 4, 
             "Sat" : 5, 
             "Sun" : 6 }

# Edges
#driving_edges = list()
#waiting_edges = list()


def create_driving_edges(input_dir, day):
    """ Generating all driving edges for the selected day
    
    Attributes:        
    input_dir : directory of the input file
    day : a specific day of the week (Mon, Tue,...) 
    """
    tree = ET.parse(input_dir)
    root = tree.getroot()
    driving_edges = list()
    
    for train in root.iter('Train'):
        train_id = train.get('TrainID_')
        
        for trip in train.iter('Trip'):
            trip_validity = trip.find('Validity').get('BitString')
            
            if trip_validity[day_dict[day]] is not "1":
                continue
            
            stop_list = list(trip.iter('Stop'))
            stop_number = len(stop_list)
            
            for i in range(1, stop_number): 
                from_station = stop_list[i-1].get('StationID')
                departure_time = stop_list[i-1].get('DepartureTime')
                to_station = stop_list[i].get('StationID')
                arrival_time = stop_list[i].get('ArrivalTime')           		
                passenger_number = stop_list[i-1].get('Passagiere')
                new_edge = tuple((from_station, departure_time, to_station, arrival_time, passenger_number))
                driving_edges.append(new_edge)
                #print(new_edge)  
                
    return driving_edges

    

def create_list_of_events(driving_edges):
    """ Create list of events 
    """
    # List of Event, which is 'a train departs from (or arrives at) a station'
    # A dictionary where key is the station and value is a list of sorted unique timestamps
    events = {}

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
        
    return events
                
                
                
def create_waiting_edges(events):
    """ Create all waiting edges for a day
    """
    waiting_edges = list()
    
    for station, timestamps in events.items():
        for i in range(len(timestamps)-1):
            new_edge = tuple((station, timestamps[i], station, timestamps[i+1], 0))
            waiting_edges.append(new_edge)
    
    return waiting_edges
                       
                       
                       
def main():
    """ Main function 
    """
    for day in day_dict: 
        for ice in ICE_NAMES: 
            input_dir = "/home/optimi/" + USERNAME +"/inputData/EN_GRIPS2019_" + ice + ".xml"
            driving_edges = create_driving_edges(input_dir, day)
            events = create_list_of_events(driving_edges)
            #for _, timestamps in events.items():
            #    print(timestamps)
            waiting_edges = create_waiting_edges(events)
            #for edge in waiting_edges:
            #    print
        print(day + ": " +str(len(driving_edges)+len(waiting_edges)))
        
    
                    
    
    
def print_to_file(filename):
    """ Output the result to a file """
    with open("sample.txt","w") as file:
        file.write(output)
    
    
    
if __name__ == "__main__":
    main()
                        
                        
                        
                        
