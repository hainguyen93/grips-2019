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
# import json

from datetime import datetime, timedelta
from dateutil.parser import parse
import matplotlib.pyplot as plt
import pandas as pd
from copy import deepcopy

from OD_matrix import *

KAPPA = 12

HOUR_TO_SECONDS = 3600

MINUTE_TO_SECONDS = 60


def construct_graph_from_file(input_dir, inspectors):
    """Construct graph from an external file

    Attributes:
        input_dir : name of the external file
        inspectors : dictionary of inspectors
    """
    print("Building graph ...", end = " ")
    t1 = time.time()

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

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))

    return graph, flow_var_names



def construct_graph(all_edges, inspectors):
    """ Construct the graph from a list of edges

    Attribute:
        all_edges : list of 6-tuples (from, depart, to, arrival, num passengers, time)
        inspectors : dict of inspectors
    """
    print("Building graph ...", end = " ")
    t1 = time.time()

    graph = nx.DiGraph() # nx.MultiDiGraph()
    flow_var_names = []

    for edge in all_edges:

        start = edge[0] + '@' + edge[1]
        end = edge[2] + '@' + edge[3]

        for k in inspectors:
            flow_var_names.append((start, end, k))

        graph.add_node(start, station = edge[0], time_stamp = edge[1])
        graph.add_node(end, station = edge[2], time_stamp = edge[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers= int(edge[4]), travel_time =int(edge[5]))

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))

    return graph, flow_var_names


#
# def save_graph(graph, file_name):
#     nx.write_gexf(graph, file_name)
#     print("graph.gexf has been saved.")
#
#
#
# def load_graph(file_name):
#     print("graph.gexf has been loaded.")
#     return nx.read_gexf(file_name)
#
# def save_data(name, dict):
#     """ Save data to json objects
#
#     Attributes:
#         name            : string name of object
#         dict            : dictionary to be saved
#     """
#     # save shortest_paths and OD to files to be read in again
#     with open(name+".json", "w") as f:
#         json.dump(dict, f)
#     print(name+".json has been saved.")
#
# def load_data(name):
#     """ Load saved data from json files
#
#     Attributes:
#         name            : string name of object
#     """
#     data = {}
#     with open(name+".json", "r") as f:
#         data = json.load(f)
#     print(name+'.json has been loaded.')
#     return data
#
# def save_variable_names(obj, name):
#     np.save(name, obj)
#     print(name+" has been saved." )
#
# def load_variable_names(name):
#     print(name+" has been loaded.")
#     return np.load(name)

def add_sinks_and_sources(graph, inspectors, flow_var_names):
    """Add sinks/sources (for each inspector) to the graph

    Attributes:
        graph : directed graph
        inspectors : dict of inspectors
        flow_var_names : list of all variables
    """
    print("Adding Sinks/Sources...", end=" ")
    t1 = time.time()

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

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))



def add_mass_balance_constraint(graph, model, inspectors, x):
    """Add the flow conservation constraints

    Attributes:
        graph : directed graph
        model : Gurobi model
        inspectors : dict of inspectors
        x : list of (binary) decision variables
    """
    print("Adding [Mass - Balance Constraint] ...", end=" ")
    t1 = time.time()

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

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))



def add_sinks_and_source_constraint(graph, model, inspectors, x):
    """Add sink/source constraint for each inspector

    Attributes:
        graph : directed graph
        model : Gurobi model
        inspectors : dict of inspectors
        x : list of binary decision variables
    """
    print("Adding [Sink and Source Constraint]...", end=" ")
    t1 = time.time()

    for k, vals in inspectors.items():
        sink = "sink_" + str(k)
        source = "source_" + str(k)
        
        in_sink_edges = [x[u, sink, k] for u in graph.predecessors(sink)]
        in_sink_edges_coefs = [1] * graph.in_degree(sink)
        sink_constr = LinExpr(in_sink_edges_coefs, in_sink_edges)
        model.addConstr(sink_constr, GRB.LESS_EQUAL, 1,"sink_constr_{}".format(k))

        out_source_edges = [x[source, u, k] for u in graph.successors(source)]
        out_source_edges_coefs = [1] * graph.out_degree(source)
        source_constr = LinExpr(out_source_edges_coefs, out_source_edges)
        model.addConstr(source_constr, GRB.LESS_EQUAL, 1,"source_constr_{}".format(k))
        
        coefs = in_sink_edges_coefs + [-1] * graph.out_degree(source)
        source_sink_balance_constr =  LinExpr(coefs, in_sink_edges + out_source_edges)
        model.addConstr(source_sink_balance_constr, GRB.EQUAL, 0, "source_sink_balance_constr_{}".format(k))

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))


def add_max_num_inspectors_constraint(graph, model, inspectors, x, max_num_inspectors):
    """Constraint to restrict the number of inspectors working on a specific day 
    by an upper bound (max_num_inspectors)
    
    Attributes:
        graph : directed graph
        model : Gurobi model
        inspectors : dict of inspectors 
        x : list of binary decision variables
        max_num_inspectors : upper bound on number of inspectors allowed to work
    """
    coefs = [1 for _ in inspectors for _ in graph.successors("source_"+str(k))]
    variables = [x["source_"+str(k),u,k] for k in inspectors for u in graph.successors("source_"+str(k))]
    constr = LinExpr(coefs, variables)
    model.addConstr(constr, GRB.EQUAL, max_num_inspectors, "max_inspectors_constr")
    


def add_time_flow_constraint(graph, model, inspectors, x):
    """Add time flow constraint (maximum number of working hours)

    Attributes:
        graph : directed graph
        model : Gurobi model
        inspectors : dict of inspectors
        x : list of binary decision variables
    """
    print("Adding [Time Flow Constraint]...", end=" ")
    t1 = time.time()

    for k, vals in inspectors.items():
        source = "source_" + str(k) + ""
        sink = "sink_" + str(k)

        ind = [x[u, sink, k] for u in graph.predecessors(sink)] + [x[source, v, k] for v in graph.successors(source)]
        val = [time.mktime(parse(graph.nodes[u]['time_stamp']).timetuple()) for u in graph.predecessors(sink)] + [-time.mktime(parse(graph.nodes[v]['time_stamp']).timetuple()) for v in graph.successors(source)]

        time_flow = LinExpr(val,ind)
        model.addConstr(time_flow,GRB.LESS_EQUAL,vals['working_hours'] * HOUR_TO_SECONDS,'time_flow_constr_{}'.format(k))

    t2 = time.time()
    print("Finished! Took {:.5f} seconds".format(t2-t1))



def minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x):
    """Add dummy variables to get rid of 'min' operators

    Attributes:
        graph : directed graph
        model : Gurobi model
        OD : origin-destination matrix
        shortest_paths : dict of edges and associated paths
    """

    print('Adding [Minimum Constraint]...', end = " ")
    t1 = time.time()

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
            model.addConstr(min_constr,GRB.LESS_EQUAL,0,"minimum_constr_path_({},{})".format(u,v))

    t2 = time.time()
    print("Finished! Took {:.5f} seconds".format(t2-t1))



def print_solution_paths(inspectors, x):
    """Print solutions
    Attributes:
        inspectors : dict of inspectors
        x : list of binary decision variables
    """
    solution = ""
    for k in inspectors:
        solution += "Inspector {} Path:".format(k)+"\n"
        solution += "------------------------------------------------------------------\n"
        # print("Inspector {} Path:".format(k))
        # print("------------------------------------------------------------------\n")
        start = "source_{}".format(k)
        while(start != "sink_{}".format(k)):
            arcs = x.select((start,'*',k))
            match = [x for x in arcs if x.getAttr("x") != 0]

            arc = match[0].getAttr("VarName").split(",")
            start = arc[1]
            arc[0] = arc[0].split("[")[1]
            arc = arc[:-1]
            solution += arc[0]+'-->'+arc[1]+ "\n"
            # print(arc)
        # print("\n------------------------------------------------------------------")
        solution += "------------------------------------------------------------------\n"
    return solution



def main(argv):
    """main function"""
    if len(argv) != 1:
        print("USAGE: {} maxNumInspectors".format(os.path.basename(__file__)))
        sys.exit()

    inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
                    1 : {"base": 'HH', "working_hours": 5, "rate": 10},
                    2 : {"base": 'AHAR', "working_hours": 6, "rate": 15}}#,
                #3 : {"base": 'FGE', "working_hours": 8, "rate": 10},
                #4 : {"base": 'HSOR', "working_hours": 7, "rate": 10},
                #5 : {"base": 'RM', 'working_hours': 5, 'rate':11}
                #}

    input_dir = '../hai_code/Mon_Arcs.txt'

    graph, flow_var_names = construct_graph_from_file(input_dir, inspectors)

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
    add_mass_balance_constraint(graph, model, inspectors, x)

    # adding sink/source constraints
    add_sinks_and_source_constraint(graph, model, inspectors, x)
    
    # add maximum number of inspectors allowed to work
    add_max_num_inspectors_constraint(graph, model, inspectors, )

    # add working_hours restriction constraints
    add_time_flow_constraint(graph, model, inspectors, x)    

    # adding dummy variables to get rid of 'min' in objective function
    minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)

    # start solving using Gurobi
    model.optimize()
        
    
    model.write("Gurobi_Solution.lp")

    # write Solution:
    solution  = print_solution_paths(inspectors, x)

    with open("Gurobi_Solution.txt", "w") as f:
        f.write(solution)



if __name__ == '__main__':
    main(sys.argv[1:])
