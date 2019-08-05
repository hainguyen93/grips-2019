# call this file to produce inspection schedule for inspectors
# @author: Hai Nguyen, Ruby Abrams and Nathan May

import sys
import os
import xml.etree.ElementTree as ET
import json
import pandas as pd
import pickle

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
    # with open(inspectors_file, "r") as f:
    #     for line in f.readlines()[1:]:
    #         line = line.split(',')
    #         inspector_id = int(line[0])
    #         depot = line[1]
    #         max_hours = float(line[2])
    #         inspectors[inspector_id] = {"base": depot, 'working_hours': max_hours}
    return inspectors


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
        print("Number of inspectors: {}".format(len(inspectors)))

        # if os.path.exists(file_name):
        #     graph = nx.read_gexf(file_name)
        # else:
        # list of 6-tuples (from, depart, to, arrival, num passengers, time)
        all_edges = extract_edges_from_timetable(timetable_file, chosen_day)

        graph = construct_graph(all_edges)

        flow_var_names = construct_variable_names(all_edges, inspectors)

        T, OD = generate_OD_matrix(deepcopy(graph))
        with open("OD.pickle","w") as f:
            pickle.dump(OD, f, protocol=pickle.HIGHEST_PROTOCOL)
        print("OD saved")
        # np.save("OD", OD)
        # print("saved OD matrix")
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
        print("Setting the objective functions...", end=" ")
        # Adding the objective function coefficients
        model.setObjective(M.prod(OD),GRB.MAXIMIZE)

        # adding flow conservation constraints
        add_mass_balance_constraint(graph, model, inspectors, x)

        # adding sink/source constraints
        add_sinks_and_source_constraint(graph, model, inspectors, max_num_inspectors, x)

        # add working_hours restriction constraints
        add_time_flow_constraint(graph, model, inspectors, x)

        shortest_paths, arc_paths = create_arc_paths(deepcopy(graph))
        # adding dummy variables to get rid of 'min' in objective function
        minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)

        # start solving using Gurobi using heuristic solution
        model.optimize()
        model.write("Inspection_LP.lp")

        # write Solution:
        solution  = print_solution_paths(inspectors, x)



        # with open(output_file, "w") as f:
        #     f.write(solution)

        # post analysis
        obj_val = float(model.objVal)
        denominator = float(sum(OD.values())(OD))
        print("Approximate number of people in the system: {}".format(denominator))
        percentage = obj_val/denominator*100
        print("Approximate percentage of people inspected today: {}%".format(percentage))
        # with open("Gurobi_Solution.txt", "w") as f:
        #     f.write(solution)

    except CommandLineArgumentsNotMatch as error:
        print(error)
        print('USAGE: {} xmlInputFile inspectorFile chosenDay outputFile'.format(os.path.basename(__file__)))
    except (ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)

    print("=======================")
    print("TESTING HEURSTIC SOLVER")
    print("=======================")

    heuristic_solver(timetable_file, chosen_day, "more_inspectors.csv","schedule_for_1_inspectors.csv", shortest_paths, OD, max_num_inspectors)

def heuristic_solver(timetable_file, chosen_day, inspectors_file, schedule_file_name, shortest_paths, OD, max_num_inspectors):
    # dictionary of id (key) and base/max_hours (value)
    inspectors = extract_inspectors_data(inspectors_file)
    all_edges = extract_edges_from_timetable(timetable_file, chosen_day)
    graph = construct_graph(all_edges)
    flow_var_names = construct_variable_names(all_edges, inspectors)
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
    add_sinks_and_source_constraint(graph, model, inspectors, max_num_inspectors, x)

    # add working_hours restriction constraints
    add_time_flow_constraint(graph, model, inspectors, x)

    # adding dummy variables to get rid of 'min' in objective function
    minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)


    # To solve problems with more inspectors, use solutions from previous problems.
    schedule = pd.read_csv(schedule_file_name)
    var_names = [(row.start_station_and_time, row.end_station_and_time, row.inspector_id) for row in schedule]

    # add heuristic solutions to solve for more inspectors
    t4 = time.time()
    def heuristic_solution(model, where):
        if where == GRB.Callback.MIPNODE:
            model.cbSetSolution(var_names, [1]*len(var_names))

    model.optimize(heuristic_solution)

    model.optimize(heuristic_solution)
    model.write("heuristic_LP.lp")

    # write Solution:
    solution = print_solution_paths(inspectors, x)
    obj_val = float(model.objVal)
    denominator = float(sum(OD.values())(OD))
    print("Approximate number of people in the system: {}".format(denominator))
    percentage = obj_val/denominator*100
    print("Approximate percentage of people inspected today: {}%".format(percentage))

if __name__ == "__main__":
    main(sys.argv[1:])
