"""Main codes for preducing the inspection schedules for multiple inspectors

INVOCATION
$ python3 main.py timetable chosenDay inspectorFile maxInspectors delta MIPGAP outputFile [--load-od]

timetable -- name of the XML file from which train timetable is extracted
            (note: must be in English, otherwise use xmltranslator.py to translate to English).
chosenDay -- a day to produce inspection shedule (e.g., Mon, Tue, etc).
inspectorFile -- name of the CSV file from which inspector data is extracted.
maxInspectors -- maximum number of inspectors allowed to work on the chosen day.
outputFile -- name of text file, where the produced inspection schedule is stored.
delta -- incremental step used in heuristic solver.
MIPGAP -- a floating point between 0 and 1 (e.g., 0.1 (~10%), 0.05 (~5%), etc)

[options] -- options to load od matrix from a file (--load-od)
          -- use the heuristic solver for large scale problem (--heuristic)

EXAMPLE:
$ python3 main.py EN_GRIPS2019_401.xml Mon inspectors.csv 30 5 0.10 schedule.txt [--load-od]
"""

import sys
import os
import xml.etree.ElementTree as ET
import json
import numpy as np
import pandas as pd

from exceptions import *
from xmlParser import *
from gurobi import *
from odMatrix import *
from readInspectorData import *
from graph import *


def main(argv):
    try:
        if len(argv) < 7:
            raise CLArgumentsNotMatch(
                'ERROR: Command-line arguments do not match')

        timetable_file = argv[0]
        chosen_day = argv[1]
        inspector_file = argv[2]
        max_num_inspectors = int(argv[3])
        mip_gap = float(argv[5])
        outputFile = argv[6]g

        delta = int(argv[4])
        if delta < 1:  # check if delta set to 0, if so, reset it to 1
            print('Note: delta can be smaller than 1. It has been reset to 1.')
            delta = 1

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found')

        edges, all_stations = extract_edges_from_timetable(
            timetable_file, chosen_day)
        inspectors = extract_inspectors_data(inspector_file, all_stations)

        if len(inspectors) < max_num_inspectors:
            print('''
                  Note: The entered maximum number of inspectors, {},
                  allowed to work on {} is greater than the total number of
                  inspectors, {}.
                  '''.format(max_num_inspectors, chosen_day, len(inspectors)))
            max_num_inspectors = len(inspectors)

        depot_dict = create_depot_inspector_dict(inspectors)

        # print out depot and inspectors
        for depot, ids in depot_dict.items():
            print('{} \t: {}'.format(depot, ids))

        #graph = construct_graph_from_edges(edges)
        #flow_var_names = construct_variable_names(edges, inspectors)
        input_dir = 'mon_arcs.txt'
        graph, flow_var_names = construct_graph_from_file(
            input_dir, inspectors)
        graph_copy = deepcopy(graph)
        shortest_paths, arc_paths = create_arc_paths(graph_copy)

        if '--load-od' in argv:
            print('Loading the OD matrix from file ...', end=' ')
            with open('savedODMatrix.txt', 'r') as f:
                data = f.read()
            OD = eval(data)
            print("Done")
        else:
            OD = generate_OD_matrix(graph_copy)

        add_sinks_and_sources_to_graph(graph, inspectors, flow_var_names)
        graph = nx.freeze(graph)  # freeze graph to prevent further changes

        print("Start Gurobi")
        model = Model("DB_INSPECTION_SCHEDULE")
        x, M = add_vars_and_obj_function(model, flow_var_names, OD)
        add_mass_balance_constraint(graph, model, inspectors, x)
        add_sinks_and_source_constraint(graph, model, inspectors, x)
        add_time_flow_constraint(graph, model, inspectors, x)
        minimization_constraint(graph, model, inspectors,
                                OD, shortest_paths, M, x)

        # important for saving constraints and variables
        model.setParam('MIPGap', mip_gap)
        model.setParam('NumericFocus', 0)

        if not '--heuristic' in argv:  # not to use heuristic
            print('No heuristic')
            add_max_num_inspectors_constraint(
                graph, model, inspectors, max_num_inspectors, x)
            model.write("Scheduling.rlp")
            model.optimize()
            solution = print_solution_paths(inspectors, x)

        else:  # use heuristic solver
            print('Use heuristic')

            # adding a max number of inspectors constraint (set to 1 by default)
            add_max_num_inspectors_constraint(graph, model, inspectors, 1, x)

            known_vars = []  # vars with known solutions
            # unknown_vars = []  # vars currently in the model
            # uncare_vars = list(inspectors.keys())   # vars currently set to zeros
            # (don't care)

            # delta = 1  # incremental number of inspector schedules to make
            # start = 1 # number of inspector schedules to start with

            prev_sols = {}

            # important for saving constraints and variables
            model.write("Scheduling.rlp")
            # model.setParam('MIPFocus', 1)

            def mycallback(model, where):
                if where == GRB.Callback.MIPNODE:
                    model.cbSetSolution(list(prev_sols.keys()),
                                        list(prev_sols.values()))
                    model.cbUseSolution()  # newly added
                    print("MODEL RUNTIME: {}".format(
                        model.cbGet(GRB.Callback.RUNTIME)))

            # initial list fill
            unknown_vars, uncare_vars = update_all_var_lists(
                [], known_vars, depot_dict, prev_sols, x)

            iteration = 0  # iteration counting

            #print('length of depot_dict == {}'.format(len(depot_dict)))
            #print('delta and length = {}'.format(min([delta, len(depot_dict)])))
            print('delta, len, max_num == {}'.format(
                min(delta, len(depot_dict), max_num_inspectors)))

            # number of inspector to start with
            new_delta = min(delta, len(depot_dict), max_num_inspectors)
            i = new_delta
            print('i=={}'.format(i))

            while True:
                iteration += 1
                print(
                    '=============== ITERATION No.{} ================'.format(iteration))
                print('''
                      Heuristic Solver is trying to find the best possible schedule
                      for at most {} inspector(s) from a set of {} inspector(s) (all in Known_Vars
                      and Unknown_Vars), where {} of them are fixed. Other inspectors
                      are set to 0
                      '''.format(new_delta, len(known_vars) + len(unknown_vars), len(known_vars)))
                print('Known Vars: ', known_vars)
                print('Unknown Vars: ', unknown_vars)
                print("Don't care Vars: ", uncare_vars)

                for uncare_inspector_id in uncare_vars:
                    arcs = x.select('*', '*', uncare_inspector_id)
                    prev_sols.update({arc: 0 for arc in arcs})

                update_max_inspectors_constraint(model, i)
                model.optimize(mycallback)
                unknown_vars, uncare_vars = update_all_var_lists(
                    unknown_vars, known_vars, depot_dict, prev_sols, x)

                if len(known_vars) >= max_num_inspectors:  # termination
                    break
                elif len(known_vars) + new_delta > max_num_inspectors:  # last iteration
                    i = max_num_inspectors
                else:
                    i = len(known_vars) + new_delta
            """
            for i in range(1, max_num_inspectors + 1, delta):

                print(
                    '=========================== ITERATION No.{} ==========================='.format(i))
                print('Known Vars: ', known_vars)
                print('Unknown Vars: ', unknown_vars)
                print("Don't care Vars: ", uncare_vars)

                for uncare_inspector_id in uncare_vars:
                    # = x.select('*', '*', uncare_inspector_id)
                    prev_sols.update(
                        {arc: 0 for arc in x.select('*', '*', uncare_inspector_id)})

                update_max_inspectors_constraint(model, i)

                model.optimize(mycallback)

                unknown_vars, uncare_vars = update_all_var_lists(
                    unknown_vars, known_vars, depot_dict, prev_sols, x)
            """

            print('==================== FINAL SOLUTION =====================')
            print('Known Vars: ', known_vars)
            print('Unknown Vars: ', unknown_vars)
            print("Don't care Vars: ", uncare_vars)

            # write Solution:
            solution = print_solution_paths(known_vars, x)

        with open(outputFile, 'w') as f:
            f.write(solution.to_string())

    except CLArgumentsNotMatch as error:
        print(error)
        sys.stderr.write(
            """USAGE:
$ python3 main.py timetable chosenDay inspectorFile maxInspectors delta MIPGAP outputFile [--load-od]

    timetable -- name of the XML file from which train timetable is extracted
            (note: must be in English, otherwise use xmltranslator.py to translate to English).
    chosenDay -- a day to produce inspection shedule (e.g., Mon, Tue, etc).
    inspectorFile -- name of the CSV file from which inspector data is extracted.
    maxInspectors -- maximum number of inspectors allowed to work on the chosen day.
    outputFile -- name of text file, where the produced inspection schedule is stored.
    delta -- incremental step used in heuristic solver.
    MIPGAP -- a floating point between 0 and 1 (e.g., 0.1 (~10%), 0.05 (~5%), etc)

    [options] -- options to load od matrix from a file (--load-od)
              -- use the heuristic solver for large scale problem (--heuristic)

EXAMPLE:
$ python3 main.py EN_GRIPS2019_401.xml Mon inspectors.csv 30 5 0.10 schedule.txt [--load-od]\n"""
        )
        sys.exit(1)

    except (CLArgumentsNotMatch, ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)


if __name__ == "__main__":
    main(sys.argv[1:])
