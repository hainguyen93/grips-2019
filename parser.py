# Create a xml parser to extract the train timetable from the input dataset
# @author(s): Hai

import xml.etree.ElementTree as ET
import datetime
import sys, os

# input dataset (translated to ENGLISH)
ice_401_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_401.xml"
#ice_402_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_402.xml"
#ice_403_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_403.xml"
#ice_411_dir = "/home/optimi/bzfnguye/inputData/EN_GRIPS2019_411.xml"

# tree for each xml file
tree_401 = ET.parse(ice_401_dir)
#tree_402 = ET.parse(ice_402_dir)
#tree_403 = ET.parse(ice_403_dir)
#tree_411 = ET.parse(ice_411_dir)

# root of xml files
root_401 = tree_401.getroot()
#root_402 = tree_402.getroot()
#root_403 = tree_403.getroot()
#root_411 = tree_411.getroot()

for train in root_401.iter('Train'):
	train_id = train.get('TrainID_')
	for trip in train.iter('Trip'):
        	trip_validity = trip.find('Validity').get('BitString')
        	stop_list = list(trip.iter('Stop'))
	    	stop_number = len(stop_list)
	    	for i in range(1, stop_number): 
			from_station = stop_list[i-1].get('StationID')
            		departure_time = stop_list[i-1].get('DepartureTime')
			to_station = stop_list[i].get('StationID')
            		arrival_time = stop_list[i].get('ArrivalTime')           		
            		passenger_number = stop_list[i-1].get('Passagiere')
			#if i is stop_number-1:  #last stop
			#	print()
            		print(from_station, departure_time, to_station, arrival_time, passenger_number)
         
         
	#print(train_id, train_validity)
	#is_first_stop = True 
	#stop = NULL
	#last_stop = NULL
	#for stop in train.iter('Stop'):
	#	#if is_first_stop:
	#	station_id = stop.get('StationID')
	#	passenger_number = stop.get('Passagiere')
	#	departure_time = 
	#	arrival_time = 		
	#	if departure_time == arrival_time:
	#print(len(list(train.iter('Stop'))))	
	

		
		
