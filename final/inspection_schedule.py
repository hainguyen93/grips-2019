# call this file to produce inspection schedule for inspectors
# @author: Hai Nguyen, Ruby Abrams and Nathan May

import sys
import os
import xml.etree.ElementTree as ET
import json
import pandas as pd

from exceptions import *
from my_xml_parser import *
from Main_Gurobi import *


def extract_inspectors_data(inspectors_file):
    """Extract a dictionary containing information for inspectors
    from the input file for inspectors

    Attribute:
        inspector_file : name of inspectors input file
    """
    data = pd.read_csv(inspectors_file)
    inspectors={ data.loc[i]['Inspector_ID']:
                    {"base": data.loc[i]['Depot'], "working_hours": data.loc[i]['Max_Hours']}
                     for i in range(len(data))}
    return inspectors


def main(argv):
    """main function"""

    if len(argv) != 1:
        print("USAGE: {} maxNumInspectors".format(os.path.basename(__file__)))
        sys.exit()

    inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
                   1 : {"base": 'HH', "working_hours": 5, "rate": 10},
                   2 : {"base": 'RDRM', "working_hours": 6, "rate": 15},
                   3 : {"base": 'HH', "working_hours": 8, "rate": 10},
                   4 : {"base": 'RDRM', "working_hours": 7, "rate": 10}
                    # 5 : {"base": 'RM', 'working_hours': 5, 'rate':11}
                    }

    depot_dict = create_depot_inspectors_dict(inspectors)

    # upper-bound max_num_inspectors by number of inspectors
    max_num_inspectors = int(argv[0])
    if max_num_inspectors > len(inspectors):
        max_num_inspectors = len(inspectors)

    input_dir = 'mon_arcs.txt'

    graph, flow_var_names = construct_graph_from_file(input_dir, inspectors)

    # OD Estimation
    shortest_paths, arc_paths = create_arc_paths(deepcopy(graph))
    # T, OD = generate_OD_matrix(graph)

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
    add_sinks_and_source_constraint(graph, model, inspectors, max_num_inspectors, x)

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

    def mycallback(model, where):
        if where == GRB.Callback.MIPNODE:
            model.cbSetSolution(list(prev_sols.keys()), list(prev_sols.values()))
            model.cbUseSolution()  # newly added
            print("MODEL RUNTIME: {}".format(model.cbGet(GRB.Callback.RUNTIME)))

    #initial list fill
    unknown_vars, uncare_vars = update_all_var_lists([], known_vars, depot_dict, x, delta)

    for i in range(1, max_num_inspectors+1, delta):
        print('============= ITERATION No.{} ============'.format(i))
        print('Known Vars:      ', known_vars)
        print('Unknown Vars:    ', unknown_vars)
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

    obj_val = float(model.objVal)
    denominator = sum(list(OD.values()))
    print("Approximate number of people in the system: {}".format(denominator))
    percentage = obj_val/denominator*100
    print("Approximate percentage of people inspected today: {}%".format(percentage))
    #
    # print("=======================")
    # print("TESTING HEURSTIC SOLVER")
    # print("=======================")

    # heuristic_solver(timetable_file, chosen_day, "more_inspectors.csv","schedule_for_1_inspectors.csv", shortest_paths, OD, max_num_inspectors)

# def heuristic_solver(timetable_file, chosen_day, inspectors_file, schedule_file_name, shortest_paths, OD, max_num_inspectors):
#     # dictionary of id (key) and base/max_hours (value)
#     inspectors = extract_inspectors_data(inspectors_file)
#     all_edges = extract_edges_from_timetable(timetable_file, chosen_day)
#     graph = construct_graph(all_edges)
#     flow_var_names = construct_variable_names(all_edges, inspectors)
#     #================================== START Gurobi ================================================
#     #                           Establish Maximization Problem
#     #================================================================================================
#     t3 = time.time()
#     print("Start Gurobi")
#     model = Model("DB_MIP");
#
#     # adding variables and objective functions
#     print("Adding variables...", end=" ")
#     x = model.addVars(flow_var_names,ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
#     M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');
#
#     # Adding the objective function coefficients
#     model.setObjective(M.prod(OD),GRB.MAXIMIZE)
#
#     # adding flow conservation constraints
#     add_mass_balance_constraint(graph, model, inspectors, x)
#
#     # adding sink/source constraints
#     add_sinks_and_source_constraint(graph, model, inspectors, max_num_inspectors, x)
#
#     # add working_hours restriction constraints
#     add_time_flow_constraint(graph, model, inspectors, x)
#
#     # adding dummy variables to get rid of 'min' in objective function
#     minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)
#
#
#     # To solve problems with more inspectors, use solutions from previous problems.
#     schedule = pd.read_csv(schedule_file_name)
#     var_names = [(row.start_station_and_time, row.end_station_and_time, row.inspector_id) for row in schedule]
#
#     # add heuristic solutions to solve for more inspectors
#     t4 = time.time()
#     def heuristic_solution(model, where):
#         if where == GRB.Callback.MIPNODE:
#             model.cbSetSolution(var_names, [1]*len(var_names))
#
#     model.optimize(heuristic_solution)
#
#     model.optimize(heuristic_solution)
#     model.write("heuristic_LP.lp")
#
#     # write Solution:
#     solution = print_solution_paths(inspectors, x)
#     obj_val = float(model.objVal)
#     denominator = float(sum(OD.values())(OD))
#     print("Approximate number of people in the system: {}".format(denominator))
#     percentage = obj_val/denominator*100
#     print("Approximate percentage of people inspected today: {}%".format(percentage))

if __name__ == "__main__":
    main(sys.argv[1:])
