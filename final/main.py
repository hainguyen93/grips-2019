"""Main codes for preducing the inspection schedules for multiple inspectors

INVOCATION:
$ python3 main.py timetable chosenDay inspectorFile maxInspectors > outputFile

timetable -- name of the XML file from which train timetable is extracted 
            (note: must be in English, otherwise use xmltranslator.py to translate to English).
chosenDay -- a day to produce inspection shedule (e.g., Mon, Tue, etc).
inspectorFile -- name of the CSV file from which inspector data is extracted.
maxInspectors -- maximum number of inspectors allowed to work on the chosen day. 
outputFile -- name of text file, where the produced inspection schedule is stored.

EXAMPLE:
$ python3 main.py EN_GRIPS2019_401.xml Mon inspectors.csv 30 > schedule.txt
"""

import sys
import os
import xml.etree.ElementTree as ET
import json
import numpy as np
import pandas as pd

from exceptions import *
from xmParser import *
from gurobi import *
from odMatrix import *
from readInspectorData import *


def main(argv):
    """Main function"""

    try:
        # raise error if command-line arguments do not match
        if len(argv) != 5:
            raise CommandLineArgumentsNotMatch('ERROR: Command-line arguments do not match')
            sys.exit()

        timetable_file = argv[0]
        inspector_file = argv[1]
        chosen_day = argv[2]
        output_file = argv[3]
        max_num_inspectors = int(argv[4])

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found')

        # dictionary of id (key) and base/max_hours (value)
        inspectors = extract_inspectors_data(inspector_file)
        print("Inspectors loaded ... number of inspectors: {}".format(len(inspectors)))

        # if os.path.exists(file_name):
        #     graph = nx.read_gexf(file_name)
        # else:
        # list of 6-tuples (from, depart, to, arrival, num passengers, time)
        all_edges = extract_edges_from_timetable(timetable_file, chosen_day)

        graph = construct_graph(all_edges)

        flow_var_names = construct_variable_names(all_edges, inspectors)

        shortest_paths, arc_paths = create_arc_paths(deepcopy(graph))

        # T, OD = generate_OD_matrix(deepcopy(graph))

        with open('../final/dict.txt','r') as f:
            data=f.read()

        OD = eval(data)
        print("OD matrix loaded ...")

        # adding sources/sinks nodes
        add_sinks_and_sources_to_graph(graph, inspectors, flow_var_names)

        #freeze graph to prevent further changes
        graph = nx.freeze(graph)

        # start Gurobi
        print("Start Gurobi")
        model = Model("DB_MIP");

        # adding variables and objective functions
        x, M = add_vars_and_obj_function(model, flow_var_names, OD)

        # adding flow conservation constraints
        add_mass_balance_constraint(graph, model, inspectors, x)

        # adding sink/source constraints
        add_sinks_and_source_constraint(graph, model, inspectors, x)

        # add working_hours restriction constraints
        add_time_flow_constraint(graph, model, inspectors, x)

        # adding dummy variables to get rid of 'min' in objective function
        minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)

        # adding a max number of inspectors constraint (set to 1 by default)
        add_max_num_inspectors_constraint(graph, model, inspectors, 1, x)

        known_vars = []  # vars with known solutions
        #unknown_vars = []  # vars currently in the model
        #uncare_vars = list(inspectors.keys())   # vars currently set to zeros (don't care)

        delta = 1 # incremental number of inspector schedules to make
        #start = 1 # number of inspector schedules to start with

        prev_sols = {}

        # important for saving constraints and variables
        model.write("Scheduling.rlp")
        model.setParam('MIPGap', 0.05)
        # model.setParam('MIPFocus', 1)
        model.setParam('NumericFocus', 0)

        def mycallback(model, where):
            if where == GRB.Callback.MIPNODE:
                model.cbSetSolution(list(prev_sols.keys()), list(prev_sols.values()))
                model.cbUseSolution()  # newly added
                print("MODEL RUNTIME: {}".format(model.cbGet(GRB.Callback.RUNTIME)))

        #initial list fill
        unknown_vars, uncare_vars = update_all_var_lists([], known_vars, depot_dict, x, delta)

        for i in range(1, max_num_inspectors+1, delta):

            print('=========================== ITERATION No.{} ==========================='.format(i))
            print('Known Vars: ', known_vars)
            print('Unknown Vars: ', unknown_vars)
            print("Don't care Vars: ", uncare_vars)

            for uncare_inspector_id in uncare_vars:
                #= x.select('*', '*', uncare_inspector_id)
                prev_sols.update({arc:0 for arc in x.select('*', '*', uncare_inspector_id)})

            update_max_inspectors_constraint(model, i)

            model.optimize(mycallback)

            unknown_vars, uncare_vars = update_all_var_lists(unknown_vars, known_vars, depot_dict, x, delta)

        # write Solution:
        solution  = print_solution_paths(known_vars, x)

        with open("Gurobi_Solution.txt", "w") as f:
            f.write(solution.to_string())

    except CommandLineArgumentsNotMatch as error:
        print(error)
        print('USAGE: {} xmlInputFile inspectorFile chosenDay outputFile'.format(os.path.basename(__file__)))

    except (ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)


if __name__ == "__main__":
    main(sys.argv[1:])
