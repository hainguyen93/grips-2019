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
    try:
        # check cl arguments
        if len(argv) != 4:
            raise CLArgumentsNotMatch('ERROR: Command-line arguments do not match')

        timetable_file = argv[0]        
        chosen_day = argv[1]        
        inspector_file = argv[2]        
        max_num_inspectors = int(argv[3])

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found')
        
        inspectors = extract_inspectors_data(inspector_file)  
        edges = extract_edges_from_timetable(timetable_file, chosen_day)
        graph = construct_graph_from_edges(edges)
        flow_var_names = construct_variable_names(edges, inspectors)        
        graph_copy = deepcopy(graph)        
        shortest_paths, arc_paths = create_arc_paths(graph_copy)

        # T, OD = generate_OD_matrix(deepcopy(graph))

        with open('savedODMatrix.txt','r') as f:
            data=f.read()
        OD = eval(data)        
        print("OD matrix loaded ...")

        add_sinks_and_sources_to_graph(graph, inspectors, flow_var_names)
        graph = nx.freeze(graph) #freeze graph to prevent further changes

        print("Start Gurobi")      
        model = Model("DB_INSPECTION_SCHEDULE");
        x, M = add_vars_and_obj_function(model, flow_var_names, OD)
        add_mass_balance_constraint(graph, model, inspectors, x)
        add_sinks_and_source_constraint(graph, model, inspectors, x)
        add_time_flow_constraint(graph, model, inspectors, x)
        minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)
        add_max_num_inspectors_constraint(graph, model, inspectors, 1, x) # default by 1

        known_vars = []  # vars with known solutions   
        delta = 1 # incremental number of inspector schedules to make
        start = 1 # number of inspector schedules to start with
        prev_sols = {} # store values of vars with known solutions

        # important for saving constraints and variables
        model.write("Scheduling.rlp")        
        model.setParam('MIPGap', 0.05)        
        # model.setParam('MIPFocus', 1)        
        model.setParam('NumericFocus', 0)

        def mycallback(model, where):
            if where == GRB.Callback.MIPNODE:
                model.cbSetSolution(list(prev_sols.keys()), list(prev_sols.values()))
                model.cbUseSolution()  
                print("MODEL RUNTIME: {}".format(model.cbGet(GRB.Callback.RUNTIME)))

        #initial list fill
        unknown_vars, uncare_vars = update_all_var_lists([], known_vars, depot_dict, x, delta)

        for i in range(start, max_num_inspectors+1, delta):

            print('====================== ITERATION No.{} ======================='.format(i))
            print('Known Vars: ', known_vars)
            print('Unknown Vars: ', unknown_vars)
            print("Don't care Vars: ", uncare_vars)

            for uncare_inspector_id in uncare_vars:
                arcs = x.select('*', '*', uncare_inspector_id)
                prev_sols.update({arc:0 for arc in arcs})

            update_max_inspectors_constraint(model, i)
            model.optimize(mycallback)
            unknown_vars, uncare_vars = update_all_var_lists(unknown_vars, known_vars, depot_dict, x, delta)

        # write solution to console
        solution  = print_solution_paths(known_vars, x)        
        print(solution.to_string())
        
    except CLArgumentsNotMatch as error:
        print(error)
        sys.stderr.write("""USAGE:
            $ python3 main.py timetable chosenDay inspectorFile maxInspectors > outputFile

                timetable -- name of the XML file from which train timetable is extracted 
                            (note: must be in English, otherwise use xmltranslator.py to translate to English).
                chosenDay -- a day to produce inspection shedule (e.g., Mon, Tue, etc).
                inspectorFile -- name of the CSV file from which inspector data is extracted.
                maxInspectors -- maximum number of inspectors allowed to work on the chosen day. 
                outputFile -- name of text file, where the produced inspection schedule is stored.

            EXAMPLE:
            $ python3 main.py EN_GRIPS2019_401.xml Mon inspectors.csv 30 > schedule.txt\n""")
        sys.exit(1)

    except (CLArgumentsNotMatch, ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)


if __name__ == "__main__":
    main(sys.argv[1:])
