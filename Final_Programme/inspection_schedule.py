# call this file to produce inspection schedule for inspectors
# @author: Hai Nguyen, Ruby Abrams and Nathan May

import sys
import os
import xml.etree.ElementTree as ET

from exceptions import *
from my_xml_parser import *
from ReformulatedLP import *
from Main_Gurobi import *


def extract_inspectors_data(inspectors_file):
    """Extract a dictionary containing information for inspectors 
    from the input file for inspectors 
    
    Attribute:
        inspector_file : name of inspectors input file
    """
    inspectors = {}
    with open(inspectors_file, "r") as f:
        for line in f.readlines()[1:]:
            line = line.split(' ')
            inspector_id = int(line[0])
            depot = line(line[1])
            max_hours = float(line[2])
            inspectors[inspector_id] = {"base": depot, 'working_hours': max_hours}
    return inspectors


def main(argv):    
    """Main function
    """
    
    try:        
        # raise error if command-line arguments do not match
        if len(argv) != 4:
            raise CommandLineArgumentsNotMatch('ERROR: Command-line arguments do not match')

        timetable_file = argv[0]
        inspector_file = argv[1]
        chosen_day = argv[2]
        output_file = argv[3]

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found! PLease check for case-sensitivity (e.g. Mon, Tue,...)')

        # list of 6-tuples (from, depart, to, arrival, num passengers, time)
        all_edges = extract_edges_from_timetable(timetable_file, chosen_day)
        
        # dictionary of id (key) and base/max_hours (value)
        inspectors = extract_inspectors_data(inspectors_file)




    except CommandLineArgumentsNotMatch as error:
        print(error)
        print('USAGE: {} xmlInputFile inspectorFile chosenDay outputFile'.format(os.path.basename(__file__)))

    except (ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)


if __name__ == "__main__":
    main(sys.argv[1:])
