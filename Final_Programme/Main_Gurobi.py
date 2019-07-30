# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# @author: Ruby Abrams, Hai Nguyen, Nate May

from __future__ import division
from gurobipy import *
from scipy import *
from scipy.sparse import *
import sys

import networkx as nx
import time
import re
import numpy as np

from datetime import datetime, timedelta
from dateutil.parser import parse
import matplotlib.pyplot as plt
import pandas as pd
from copy import deepcopy

from OD_matrix import *

KAPPA = 12

HOUR_TO_SECONDS = 3600

MINUTE_TO_SECONDS = 60


#============================= PROGRAM FUNCTIONS ============================================

def construct_graph_from_file(input_dir, inspectors):
    """Construct graph from external file
    """
    graph = nx.DiGraph() # nx.MultiDiGraph()
    flow_var_names = []
    
    with open(input_dir, "r") as f:
        for line in f.readlines()[:-1]:
            line = line.replace('\n','').split(' ')
            start = line[0]+'@'+line[1]
            end = line[2]+'@'+line[3]

            for k in inspectors:
                flow_var_names.append((start, end, k))

            graph.add_node(start, station = line[0], time_stamp = line[1])
            graph.add_node(end, station = line[2], time_stamp = line[3])

            # we assume a unique edge between events for now
            if not graph.has_edge(start, end):
                graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))
    return graph, flow_var_names


def construct_graph(all_edges, inspectors):
    """ Construct the graph from a list of edges
    
    Attribute:
        all_edges : list of 6-tuples (from, depart, to, arrival, num passengers, time)    
    """
    graph = nx.DiGraph() # nx.MultiDiGraph()
    flow_var_names = []
    
    for edge in all_edges:
       
        start = edge[0] + '@' + edge[1]
        end = edge[2] + '@' + edge[3]
        
        for k in inspectors:
            flow_var_names.append((start, end, k))

        graph.add_node(start, station = line[0], time_stamp = line[1])
        graph.add_node(end, station = line[2], time_stamp = line[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))
            
    return graph, flow_var_names


def add_sinks_and_sources(graph, inspectors, flow_var_names):
    for k, vals in inspectors.items():
        source = "source_" + str(k)
        sink = "sink_"+str(k)
        graph.add_node(source, station = vals['base'], time_stamp = None)
        graph.add_node(sink, station = vals['base'], time_stamp = None)
        for node in graph.nodes():
            if (graph.nodes[node]['station'] == vals['base']) and (graph.nodes[node]['time_stamp'] is not None):
                # adding edge between sink and events and adding to the variable dictionary
                graph.add_edge(source, node, num_passengers = 0, travel_time = 0)
                flow_var_names.append((source, node, k))
                graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
                flow_var_names.append((node, sink, k))


def add_mass_balance_constraint(graph, model, inspectors):
    for k in inspectors:
        for node in graph.nodes():
            if graph.nodes[node]['time_stamp']:

                in_x = [] #list of in_arc variables

                for p in graph.predecessors(node):
                    if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k): # not a sink/source
                        in_x.append(x[p, node, k])

                in_vals = [1] * len(in_x)
                in_exp = LinExpr(in_vals,in_x)

                out_x = [] #list of out-arc variables

                for p in graph.successors(node):
                    if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k):
                        out_x.append(x[node, p, k])

                out_vals = [-1] * len(out_x)
                out_exp = LinExpr(out_vals,out_x)

                in_exp.add(out_exp) #combine in-arc & out-arc linear expressions
                model.addConstr(in_exp,GRB.EQUAL,0,"mass_bal_{}_{}".format(node,str(k))) #add constraint to model


def add_sinks_and_source_constraint(graph, model, inspectors):
    for k, vals in inspectors.items():
        sink = "sink_" + str(k)
        source = "source_" + str(k)

        sink_constr = LinExpr([1] * graph.in_degree(sink),[x[u, sink, k] for u in graph.predecessors(sink)])
        model.addConstr(sink_constr, GRB.EQUAL, 1,"sink_constr_{}".format(k))

        source_constr = LinExpr([1] * graph.out_degree(source),[x[source, u, k] for u in graph.successors(source)])
        model.addConstr(source_constr, GRB.EQUAL, 1,"source_constr_{}".format(k))


def add_time_flow_constraint(graph, model, inspectors):
    for k, vals in inspectors.items():
        source = "source_" + str(k) + ""
        sink = "sink_" + str(k)

        ind = [x[u, sink, k] for u in graph.predecessors(sink)] + [x[source, v, k] for v in graph.successors(source)]
        val = [time.mktime(parse(graph.nodes[u]['time_stamp']).timetuple()) for u in graph.predecessors(sink)] + [-time.mktime(parse(graph.nodes[v]['time_stamp']).timetuple()) for v in graph.successors(source)]

        time_flow = LinExpr(val,ind)
        model.addConstr(time_flow,GRB.LESS_EQUAL,vals['working_hours'] * HOUR_TO_SECONDS,'time_flow_constr_{}'.format(k))


def minimization_constraint(graph, model, inspectors, OD, shortest_paths):
    # Create a dictionary of all Origin-Destinations
    all_paths = {}
    for source, sink in OD.keys():
        if source != sink:
            all_paths[(source, sink)] = shortest_paths[source][sink]

    for (u, v), path in all_paths.items():
        if not ("source_" in u+v or "sink_" in u+v):

            indices = [M[u,v]] + [x[i,j,k] for i,j in zip(path, path[1:]) for k in inspectors]
            values = [1] + [-KAPPA * graph.edges[i,j]['travel_time']/graph.edges[i,j]['num_passengers'] for i,j in zip(path, path[1:]) for k in inspectors]

            min_constr = LinExpr(values,indices)
            model.addConstr(min_constr,GRB.EQUAL,0,"minimum_constr_path_({},{})".format(u,v))


def print_solution_paths(inspectors, x):
    for k in inspectors:
        print("Inspector {} Path:".format(k))
        print("------------------------------------------------------------------\n")
        start = "source_{}".format(k)
        while(start != "sink_{}".format(k)):
            arcs = x.select((start,'*',k))
            match = [x for x in arcs if x.getAttr("x") != 0]

            arc = match[0].getAttr("VarName").split(",")
            start = arc[1]
            arc[0] = arc[0].split("[")[1]
            arc = arc[:-1]

            print(arc)
        print("\n------------------------------------------------------------------")
        
        
def main():
    """main function"""
    
    inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
                1 : {"base": 'HH', "working_hours": 5, "rate": 10},
                2 : {"base": 'AHAR', "working_hours": 6, "rate": 15}}#,
                #3 : {"base": 'FGE', "working_hours": 8, "rate": 10},
                #4 : {"base": 'HSOR', "working_hours": 7, "rate": 10},
                #5 : {"base": 'RM', 'working_hours': 5, 'rate':11}
                #}                

    input_dir = '../hai_code/Mon_Arcs.txt'     

    print("Building graph ...", end = " ")
    t1 = time.time()

    graph, flow_var_names = construct_graph_from_file(input_dir)

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


    t2a = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2a-t2))

    #============================== ADDING SOURCE/SINK NODES ==========================================

    print("Adding Sinks/Sources...", end=" ")

    add_sinks_and_sources(graph, inspectors, flow_var_names)

    t3 = time.time()

    print('Finished! Took {:.5f} seconds'.format(t3-t2a))

    # test edge source to sinks
    # print('TEST: Unique edge between two nodes: ', num_edges == graph.number_of_edges())
    # print("TEST: No Source-Sink Edge: ", not graph.has_edge("source_0", "sink_0"))

    # freeze graph to prevent further changes
    graph = nx.freeze(graph)

    #================================== START Gurobi ================================================
    #                           Establish Maximization Problem
    #================================================================================================
            
    print("Start Gurobi")

    model = Model("DB_MIP");

    #========================= ADDING VARIABLES AND OBJECTIVE FUNCTION ==============================

    print("Adding variables...", end=" ")

    x = model.addVars(flow_var_names,ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
    M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');

    # Adding the objective function coefficients
    model.setObjective(M.prod(OD),GRB.MAXIMIZE)

    t4 = time.time()
    print("Finished! Took {:.5f} seconds".format(t4-t3))

    #=================================== CONSTRAINT 6 ===================================================
    #                              Mass - Balance Constraint
    #================================================================================================
    print("Adding Constraint (6) [Mass - Balance Constraint] ...", end=" ")

    add_mass_balance_constraint(graph, model, inspectors)

    t5 = time.time()

    print('Finished! Took {:.5f} seconds'.format(t5-t4))


    #=================================== CONSTRAINT 7 ===============================================
    #                              Sink and Source Constraint
    #================================================================================================

    print("Adding constraint (7) [Sink and Source Constraint]...", end=" ")

    add_sinks_and_source_constraint(graph, model, inspectors)

    t6 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t6-t5))


    #===================================== CONSTRAINT 8 ==================================================
    #                        Time Flow/Number of Working Hours Constraint
    #================================================================================================

    print("Adding Constraint (8) [Time Flow Constraint]...", end=" ")

    add_time_flow_constraint(graph, model, inspectors)

    t7 = time.time()
    print("Finished! Took {:.5f} seconds".format(t7-t6))


    #================================== CONSTRAINT 9 ==========================================
    #                   Minimum Constraint (Linearizing the Objective Function)
    #================================================================================================

    print('Adding Constraint (9) [Minimum Constraint]...', end = " ")


    minimization_constraint(graph, model, inspectors, OD, shortest_paths)

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




if __name__ == '__main__':
    main()
