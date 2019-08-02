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
        if len(argv) != 5:
            raise CommandLineArgumentsNotMatch('ERROR: Command-line arguments do not match')
            sys.exit()

        timetable_file = argv[0]
        inspector_file = argv[1]
        chosen_day = argv[2]
        output_file = argv[3]
        # options = argv[4]
	max_num_inspectors = int(argv[4])

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found! Please check for case-sensitivity (e.g. Mon, Tue,...)')

        # shortest_paths = {}
        # OD = {}
        # graph = None
        # flow_var_names = []
        # inspectors = []

        # if options == '--load-data':
        #     try:
        # list of 6-tuples (from, depart, to, arrival, num passengers, time)
        all_edges = extract_edges_from_timetable(timetable_file, chosen_day)
        # dictionary of id (key) and base/max_hours (value)
        inspectors = extract_inspectors_data(inspector_file)

        # shortest_paths = load_data("shortest_paths.json")
        # OD = load_data("OD.json")
        # graph = load_graph("graph.gexf")
        # flow_var_names = load_variable_names("flow_var_names.npy")

        #     except FileNotFoundError as error:
        #         print(error)
        #         print("Run the program without '--load-data' option.")
        #         print("Next time the program is run, '--load-data' can be omitted.")
        #         print("The saved data will be automatically loaded")
        # elif options == '--make-data':

        graph, flow_var_names = construct_graph(all_edges, inspectors)

        shortest_paths, arc_paths = create_arc_paths(deepcopy(graph))

        T, OD = generate_OD_matrix(graph.nodes(), shortest_paths, arc_paths)

        # save shortest_paths and OD coefficients data
        # save_data("shortest_paths",shortest_paths)
        # save_data("OD", OD)

        add_sinks_and_sources(graph, inspectors, flow_var_names)

        # freeze graph to prevent further changes
        graph = nx.freeze(graph)

        # save_graph(graph, "graph.gexf")
        # save_variable_names(flow_var_names, "flow_var_names.npy")

        #================================== START Gurobi ================================================
        #                           Establish Maximization Problem
        #================================================================================================
        t3 = time.time()
        print("Start Gurobi")
        model = Model("DB_MIP");

        # adding variables and objective functions
        print("Adding variables...", end=" ")
        x = model.addVars(flow_var_names,ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
        M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');

        # Adding the objective function coefficients
        model.setObjective(M.prod(OD),GRB.MAXIMIZE)

        # adding flow conservation constraints
        add_mass_balance_constraint(graph, model, inspectors, x)

        # adding sink/source constraints
        add_sinks_and_source_constraint(graph, model, inspectors, x)

	# add max number of inspectors working
	add_max_num_inspectors_constraint(graph, model, inspectors, x, max_num_inspectors)

        # add working_hours restriction constraints
        add_time_flow_constraint(graph, model, inspectors, x)

        # adding dummy variables to get rid of 'min' in objective function
        minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)

        # start solving using Gurobi
        model.optimize()
        model.write("Gurobi_Solution.lp")

        # write Solution:
        solution  = print_solution_paths(inspectors, x)

        with open(output_file, "w") as f:
            f.write(solution)

    except CommandLineArgumentsNotMatch as error:
        print(error)
        print('USAGE: {} xmlInputFile inspectorFile chosenDay outputFile'.format(os.path.basename(__file__)))

    except (ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)



if __name__ == "__main__":
    main(sys.argv[1:])
