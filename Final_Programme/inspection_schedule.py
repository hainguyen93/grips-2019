# call this file to produce inspection schedule for inspectors
# @author: Hai Nguyen, Ruby Abrams and Nathan May

import sys
import os
import xml.etree.ElementTree as ET

from exceptions import *
from my_xml_parser import *
from ReformulatedLP import *


def main(argv):
    try:
        # raise error if command-line arguments do not match
        if len(argv) != 3:
            raise CommandLineArguments('ERROR: Command-line arguments do not match')

        timetable_file = argv[0]
        inspectors_file = argv[1]
        selected_day = argv[2]

        if not selected_day in DAY_DICT:
            raise DayNotFound('ERROR: Selected day is not found. Please check for case-sensitivity')

        all_edges = extract_edges_from_timetable(timetable_file, selected_day)
        
        inspectors = extract_inspectors_data(inspectors_file)




    except CommandLineArguments as error:
        print(error)
        print('USAGE: {} timetable inspectors day'.format(os.path.basename(__file__)))

    except ET.ParseError as error:
        print(error)

    except DayNotFound as error:
        print(error)

    except FileNotFoundError as error:
        print(error)



# extract a dictionary containing information for inspectors
# (id, max_hours) from the inspectors.csv file
def extract_inspectors_data(inspectors_file):
    inspectors = {}
    with open(inspectors_file, "r") as f:
        for line in f.readlines()[1:]:
            line = line.split(' ')
            inspector_id = int(line[0])
            depot = line(line[1])
            max_hours = float(line[2])
            inspectors[inspector_id] = {"base": depot, 'working_hours': max_hours}
    return inspectors



if __name__ == "__main__":
    main(sys.argv[1:])
