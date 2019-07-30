# call this file to produce inspection schedule for inspectors
# @author: Hai Nguyen, Ruby Abrams and Nathan May

import sys
import os
import xml.etree.ElementTree as ET
import json

from exceptions import *
from my_xml_parser import *
# from ReformulatedLP import *
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
            line = line.split(',')
            inspector_id = int(line[0])
            depot = line[1]
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
            sys.exit()

        timetable_file = argv[0]
        inspector_file = argv[1]
        chosen_day = argv[2]
        output_file = argv[3]

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found! Please check for case-sensitivity (e.g. Mon, Tue,...)')

        # list of 6-tuples (from, depart, to, arrival, num passengers, time)
        all_edges = extract_edges_from_timetable(timetable_file, chosen_day)

        # dictionary of id (key) and base/max_hours (value)
        inspectors = extract_inspectors_data(inspector_file)

        # constructing the directed graph
        graph, flow_var_names = construct_graph(all_edges, inspectors)

        # OD Estimation     
        shortest_paths, arc_paths = create_arc_paths(deepcopy(graph))
        T, OD = generate_OD_matrix(graph.nodes(), shortest_paths, arc_paths)   

        # adding sources/sinks nodes  
        add_sinks_and_sources(graph, inspectors, flow_var_names)
        
        #freeze graph to prevent further changes    
        graph = nx.freeze(graph)

        # start Gurobi
        print("Start Gurobi")
        model = Model("DB_MIP");

        # adding variables and objective functions
        print("Adding variables...", end=" ")
        x = model.addVars(flow_var_names,ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
        M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');

        # Adding the objective function coefficients
        model.setObjective(M.prod(OD),GRB.MAXIMIZE)
        
        # adding flow conservation constraints
        add_mass_balance_constraint(graph, model, inspectors)

        # adding sink/source constraints
        add_sinks_and_source_constraint(graph, model, inspectors)
        
        # add working_hours restriction constraints
        add_time_flow_constraint(graph, model, inspectors)

        # adding dummy variables to get rid of 'min' in objective function
        minimization_constraint(graph, model, inspectors, OD, shortest_paths)   

        # start solving using Gurobi
        model.optimize()
        model.write("Gurobi_Solution.lp")

        # write Solution:
        solution  = print_solution_paths(inspectors, x)
        
        with open("Gurobi_Solution.txt", "w") as f:
            f.write(solution)

    except CommandLineArgumentsNotMatch as error:
        print(error)
        print('USAGE: {} xmlInputFile inspectorFile chosenDay outputFile'.format(os.path.basename(__file__)))

    except (ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)



if __name__ == "__main__":
    main(sys.argv[1:])
    
