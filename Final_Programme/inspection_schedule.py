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
        if len(argv) < 4:
            raise CommandLineArgumentsNotMatch('ERROR: Command-line arguments do not match')
            sys.exit()

        timetable_file = argv[0]
        inspector_file = argv[1]
        chosen_day = argv[2]
        output_file = argv[3]
        # options = argv[4]

        if not chosen_day in DAYS:
            raise DayNotFound('ERROR: Day not found! Please check for case-sensitivity (e.g. Mon, Tue,...)')

        shortest_paths = {}
        OD = {}
        graph = None

        # if options == '--load-data':
        try:
            shortest_paths = load_data("shortest_paths.json")
            OD = load_data("OD.json")
            graph = load_graph("graph.gexf")
        except FileNotFoundError as error:
            # list of 6-tuples (from, depart, to, arrival, num passengers, time)
            all_edges = extract_edges_from_timetable(timetable_file, chosen_day)
            # dictionary of id (key) and base/max_hours (value)
            inspectors = extract_inspectors_data(inspector_file)
            print("Building graph ...", end = " ")
            t1 = time.time()

            graph, flow_var_names = construct_graph(all_edges, inspectors)

            # time to build graph
            t2 = time.time()

            print('Finished! Took {:.5f} seconds'.format(t2-t1))

            #================================ OD Estimation ===============================
            print("Estimating OD Matrix ...", end = " ")

            # create a deep copy of the graph
            new_graph = deepcopy(graph)

            nodes = graph.nodes()

            shortest_paths, arc_paths = create_arc_paths(new_graph)

            T, OD = generate_OD_matrix(nodes, shortest_paths, arc_paths)

            # save shortest_paths and OD coefficients data
            save_data("shortest_paths",shortest_paths)
            save_data("OD", OD)

            t2a = time.time()
            print('Finished! Took {:.5f} seconds'.format(t2a-t2))

            #============================== ADDING SOURCE/SINK NODES ==========================================

            print("Adding Sinks/Sources...", end=" ")

            add_sinks_and_sources(graph, inspectors, flow_var_names)

            t3 = time.time()

            print('Finished! Took {:.5f} seconds'.format(t3-t2a))

            # freeze graph to prevent further changes
            graph = nx.freeze(graph)

            save_graph(graph, "graph.gexf")
            print(error)
            print("Data has been saved. Run the program again.")


        #================================== START Gurobi ================================================
        #                           Establish Maximization Problem
        #================================================================================================

        print("Start Gurobi")

        model = Model("DB_MIP");

        #========================= ADDING VARIABLES AND OBJECTIVE FUNCTION ==============================

        print("Adding variables...", end=" ")

        x = model.addVars(list(set(flow_var_names)),ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
        M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');

        # Adding the objective function coefficients
        model.setObjective(M.prod(OD),GRB.MAXIMIZE)

        t4 = time.time()
        print("Finished! Took {:.5f} seconds".format(t4-t3))

        #=================================== CONSTRAINT 6 ===================================================
        #                              Mass - Balance Constraint
        #================================================================================================
        print("Adding Constraint (6) [Mass - Balance Constraint] ...", end=" ")

        add_mass_balance_constraint(graph, model, inspectors, x)

        t5 = time.time()

        print('Finished! Took {:.5f} seconds'.format(t5-t4))


        #=================================== CONSTRAINT 7 ===============================================
        #                              Sink and Source Constraint
        #================================================================================================

        print("Adding constraint (7) [Sink and Source Constraint]...", end=" ")

        add_sinks_and_source_constraint(graph, model, inspectors, x)

        t6 = time.time()
        print('Finished! Took {:.5f} seconds'.format(t6-t5))


        #===================================== CONSTRAINT 8 ==================================================
        #                        Time Flow/Number of Working Hours Constraint
        #================================================================================================

        print("Adding Constraint (8) [Time Flow Constraint]...", end=" ")

        add_time_flow_constraint(graph, model, inspectors, x)

        t7 = time.time()
        print("Finished! Took {:.5f} seconds".format(t7-t6))


        #================================== CONSTRAINT 9 ==========================================
        #                   Minimum Constraint (Linearizing the Objective Function)
        #================================================================================================

        print('Adding Constraint (9) [Minimum Constraint]...', end = " ")


        minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)

        t8 = time.time()
        print("Finished! Took {:.5f} seconds".format(t8-t7))


        #================================== POST-PROCESSING ================================================

        model.optimize()
        model.write("Gurobi_Solution.lp")

        #Write Solution:
        #----------------------------------------------------------------------------------------------

        #with open("Gurobi_Solution.txt", "w") as f:
        #f.write()

        #Print Solution Paths:
        #----------------------------------------------------------------------------------------------
        print_solution_paths(inspectors, x)



    except CommandLineArgumentsNotMatch as error:
        print(error)
        print('USAGE: {} xmlInputFile inspectorFile chosenDay outputFile'.format(os.path.basename(__file__)))

    except (ET.ParseError, DayNotFound, FileNotFoundError) as error:
        print(error)


if __name__ == "__main__":
    main(sys.argv[1:])
