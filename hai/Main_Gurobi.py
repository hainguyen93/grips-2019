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



def construct_graph(all_edges):
    """ Construct the graph from a list of edges
    Attribute:
        all_edges : list of 6-tuples (from, depart, to, arrival, num passengers, time)
    """
    print("Building graph ...", end = " ")
    t1 = time.time()

    graph = nx.DiGraph() # nx.MultiDiGraph()
    flow_var_names = []

    for edge in all_edges:

        start = edge[0] + '@' + edge[1]
        end = edge[2] + '@' + edge[3]

        graph.add_node(start, station = edge[0], time_stamp = edge[1])
        graph.add_node(end, station = edge[2], time_stamp = edge[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers= int(edge[4]), travel_time =int(edge[5]))

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))

    return graph #, flow_var_names


def construct_variable_names(all_edges, inspectors):
    flow_var_names = []
    for edge in all_edges:
        start = edge[0] + '@' + edge[1]
        end = edge[2] + '@' + edge[3]
        flow_var_names.append([(start, end, k) for k in inspectors])
    return flow_var_names
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



def add_sinks_and_sources_to_graph(graph, inspectors, flow_var_names):
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

        sink_constr = LinExpr([-1] * graph.in_degree(sink),[x[u, sink, k] for u in graph.predecessors(sink)])
        #model.addConstr(sink_constr, GRB.EQUAL, 1,"sink_constr_{}".format(k))

        source_constr = LinExpr([1] * graph.out_degree(source),[x[source, u, k] for u in graph.successors(source)])
        sink_constr.add(source_constr) #combine

        model.addConstr(sink_constr, GRB.EQUAL, 0,"source_constr_{}".format(k))
        model.addConstr(source_constr, GRB.LESS_EQUAL, 1,"source_constr_{}".format(k))

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))



def add_max_num_inspectors_constraint(graph, model, inspectors, max_num_inspectors, x):
    """Adding a maximum number of inspectors constraint
    Attributes:
        graph : directed graph
        model : Gurobi model
        inspectors : dict of inspectors
        x : list of binary decision variables
    """

    print("Adding [Max Working Inspectors Constraint]...", end=" ")
    t1 = time.time()

    for k, vals in inspectors.items():
        source = "source_" + str(k)

        source_constr = LinExpr([1] * graph.out_degree(source),[x[source, u, k] for u in graph.successors(source)])

        if k == 0:
            maxWorking = source_constr
        else:
            maxWorking.add(source_constr)

    model.addConstr(maxWorking, GRB.LESS_EQUAL, max_num_inspectors,name="Max_Inspector_Constraint")

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2-t1))



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
    solution = pd.DataFrame(columns = ['start_station_and_time','end_station_and_time','inspector_id'])
    for k in inspectors:
        start = "source_{}".format(k)
        while(start != "sink_{}".format(k)):
            arcs = x.select(start,'*',k)
            match = [x for x in arcs if x.getAttr("x") > 0.5]
            arc = match[0].getAttr("VarName").split(",")
            arc[0] = arc[0].split("[")[1]
            arc = arc[:-1]
            start = arc[1]
            solution = solution.append({'start_station_and_time': arc[0],
                                        'end_station_and_time': arc[1],
                                        'inspector_id':k}, ignore_index=True)
    solution.to_csv("schedule_for_{}_inspectors.csv".format(len(inspectors)))
    return solution



def create_depot_inspectors_dict(inspectors):
    """Create a new dict with keys being depot and value being a list of
    inspector_id, sorted in descending order according
    to the max_working_hours
    
    Attributes:
        inspectors : dict of inspectors
    """
    res = dict()
    for inspector, val in inspectors.items():
        if not val['base'] in res:
            res[val['base']] = [(inspector, val['working_hours'])]
        else:
            res[val['base']].append((inspector, val['working_hours']))

    for _, val in res.items():
        val.sort(key=lambda x: x[1], reverse=True)
    return {k:[i[0] for i in val] for k, val in res.items()}



def select_inspectors_from_each_depot(depot_dict, delta, known_vars, unknown_vars, uncare_vars):
    """Select the (delta) inspectors with the largest number of working hours
    from each depot
    
    Attributes:
        depot_dict : dict of depot as keys and list of (inspector_id, max_hours) as values
        delta : maximum number of inspectors drawn from each depot
        known_vars : list of vars whose values are known (solved)
        uncare_vars : list of vars whose values are made 0 (do not contribute to maximum inspection number)
    """
    for depot, val in depot_dict.items():
        count = 0
        for inspector_id in val:
            if inspector_id in known_vars:
                continue
            if count < delta:
                if not inspector_id in unknown_vars:
                    unknown_vars.append(inspector_id) # add to unknown_vars
                    uncare_vars.remove(inspector_id)  # remove from don't care vars
                count += 1
            else:
                break



def update_all_var_lists(known_vars, unknown_vars, x):
    """Update the lists of variables
    """
    for inspector_id in unknown_vars[:]:
<<<<<<< HEAD
=======
        if [z for z in x.select('*','*',inspector_id) if z.getAttr('x') >= .9 ]:  # inspector involves in solution
            known_vars.append(inspector_id)
            #unknown_vars.remove(inspector_id) --- Don't need anymore
            # find base 'key' where inspector_id lives, in order to delete from depot_dict:
            inspector_id_base = [base for base in depot_dict.keys() if inspector_id in depot_dict[base]]

            # now remove it from depot dict:
            depot_dict[inspector_id_base[0]].remove(inspector_id)

    # update unknown and uncare vars:
    unknown_vars = []
    uncare_vars = []
    for inspectors in depot_dict.values():
        if len(inspectors) > delta:
            unknown_vars = unknown_vars + inspectors[:delta]
            uncare_vars = uncare_vars + inspectors[delta:]
        else:
            unknown_vars = unknown_vars + inspectors
    return unknown_vars, uncare_vars



            #all_arcs = x.select('*', '*', inspector_id)
            #prev_sols.update({arc.getAttr('VarName'):clean_up_sol(x.getAttr('x')) for arc in all_arcs})
    #=========================================================================================

    '''for inspector_id in unknown_vars[:]:
>>>>>>> 2a15574ab12be2874eafb7dd43ceed2eb94aeb56
        start = "source_{}".format(inspector_id)
        source_arcs = x.select(start, '*', inspector_id)
        source_sols = [clean_up_sol(arc.getAttr('x')) for arc in source_arcs]
        if sum(source_sols) == 1:  # inspector involves in solution
            known_vars.append(inspector_id)
            unknown_vars.remove(inspector_id)
            


def update_max_inspectors_constraint(model, new_max_inspectors):
    """ Update the max_num_inspectors in the model constraint named
    'Max_Inspector_Constraint', and also write the lp model to a file
    
    Attributes:
        model : Gurobi model
        new_max_inspectors : new upper bound on maximum number of inspectors
    """
    constr = model.getConstrByName("Max_Inspector_Constraint")
    constr.setAttr(GRB.Attr.RHS, new_max_inspectors)
    model.update() # implement all pending changes
    model.write("gurobi_model_{}.lp".format(new_max_inspectors))



def add_vars_and_obj_function(model, flow_var_names, OD):
    """Adding variables and objective function to model
    
    Attributes:
        model : Gurobi model
        flow_var_names : list of binary variables
        OD : origin-destination matrix
    """
    print("Adding variables...", end=" ")

    # adding variables
    x = model.addVars(flow_var_names,ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
    M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');

    # Adding the objective function coefficients
    model.setObjective(M.prod(OD),GRB.MAXIMIZE)

    print('Done')
    return x, M



def clean_up_sol(x):
    return 1 if x > 0.5 else 0



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

    depot_inspector_dict = create_depot_inspectors_dict(inspectors)

    # upper-bound max_num_inspectors by number of inspectors
    max_num_inspectors = int(argv[0])
    if max_num_inspectors > len(inspectors):
        max_num_inspectors = len(inspectors)

    input_dir = 'Mon_Arcs.txt'

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
    add_sinks_and_source_constraint(graph, model, inspectors, x)

    # add working_hours restriction constraints
    add_time_flow_constraint(graph, model, inspectors, x)

    # adding dummy variables to get rid of 'min' in objective function
    minimization_constraint(graph, model, inspectors, OD, shortest_paths, M, x)

    # adding a max number of inspectors constraint
    add_max_num_inspectors_constraint(graph, model, inspectors, 1, x)

    known_vars = []  # vars with known solutions
    unknown_vars = []  # vars currently in the model
    uncare_vars = list(inspectors.keys())   # vars currently set to zeros (don't care)

    delta = 1 # incremental number of inspector schedules to make
    start = 0 # number of inspector schedules to start with

    prev_sols = {}

    # important for saving constraints and variables
    model.write("Scheduling.rlp")
    model.setParam('MIPGap', 0.1)
    # model.setParam('MIPFocus', 1)

    def mycallback(model, where):
        if where == GRB.Callback.MIPNODE:
            model.cbSetSolution(list(prev_sols.keys()), list(prev_sols.values()))
            print("MODEL RUNTIME: {}".format(model.cbGet(GRB.Callback.RUNTIME)))


    t = time.time()
    
    for i in range(start, max_num_inspectors, delta):

        select_inspectors_from_each_depot(depot_inspector_dict, delta, known_vars, unknown_vars, uncare_vars)
        
        print(known_vars)
        print("========")
        print(unknown_vars)
        print("========")
        print(uncare_vars)
        
        for uncare_inspector_id in uncare_vars:
            all_vars = x.select('*', '*', uncare_inspector_id)
            prev_sols.update({arc:0 for arc in all_vars})

        update_max_inspectors_constraint(model, i)

        model.optimize(mycallback)

        update_all_var_lists(known_vars, unknown_vars, x)

    # write Solution:
    solution  = print_solution_paths(known_vars, x)

    with open("Gurobi_Solution.txt", "w") as f:
        f.write(solution.to_string())



if __name__ == '__main__':
    main(sys.argv[1:])
