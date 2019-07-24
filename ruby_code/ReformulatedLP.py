# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# @author: Ruby Abrams, Hai Nguyen, Nate May

from __future__ import division

import sys

# change local PATH environment for Python
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')

import cplex
import networkx as nx
import time
import re
from scipy import *
from scipy.sparse import *
import numpy as np
#import Logger  # print out to file
from datetime import datetime, timedelta
from dateutil.parser import parse
import matplotlib.pyplot as plt
import pandas as pd
from copy import deepcopy

from OD_matrix import *

# networkx start
graph = nx.DiGraph() # nx.MultiDiGraph()

inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
              1 : {"base": 'HH', "working_hours": 5, "rate": 10},
              2 : {"base": 'AHAR', "working_hours": 6, "rate": 15}}

#inspectors = {0: {"base": 'C', "working_hours":1},
              #1: {"base": 'A', "working_hours":1}}
# Assumption: rate of inspection remains constant
KAPPA = 12
flow_var_names = []

# new reformulation variable
var_portion_of_passengers_inspected = np.array([])

HOUR_TO_SECONDS = 3600
MINUTE_TO_SECONDS = 60


input_dir = '../hai_code/Mon_Arcs.txt' # /home/optimi/bzfnguye/grips-2019
#input_dir = '../Nate/Small_Train_Schedule.txt'

#============================= CONSTRUCTING THE GRAPH ============================================

print("Building graph ...", end = " ")
t1 = time.time()

with open(input_dir, "r") as f:
    for line in f.readlines()[:-1]:
        line = line.replace('\n','').split(' ')
        start = line[0]+'@'+line[1]
        end = line[2]+'@'+line[3]

        for k in inspectors:
            flow_var_names.append('var_x_{}_{}_{}'.format(start, end, k))

        graph.add_node(start, station = line[0], time_stamp = line[1])
        graph.add_node(end, station = line[2], time_stamp = line[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))


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

# Create a dictionary of all Origin-Destinations
all_paths = {}
for source, sink in OD.keys():
    if source != sink:
        all_paths[(source, sink)] = shortest_paths[source][sink]

path_idx = {path:i for i,path in enumerate(all_paths)}


t2a = time.time()
print('Finished! Took {:.5f} seconds'.format(t2a-t2))

#============================== ADDING SOURCE/SINK NODES ==========================================

print("Adding Sinks/Sources...", end=" ")

for k, vals in inspectors.items():
    source = "source_" + str(k)
    sink = "sink_"+str(k)
    graph.add_node(source, station = vals['base'], time_stamp = None)
    graph.add_node(sink, station = vals['base'], time_stamp = None)
    for node in graph.nodes():
        if (graph.nodes[node]['station'] == vals['base']) and (graph.nodes[node]['time_stamp'] is not None):
            # adding edge between sink and events and adding to the variable dictionary
            graph.add_edge(source, node, num_passengers = 0, travel_time = 0)
            flow_var_names.append('var_x_{}_{}_{}'.format(source, node, k))
            graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
            flow_var_names.append('var_x_{}_{}_{}'.format(node, sink, k))


t3 = time.time()

print('Finished! Took {:.5f} seconds'.format(t3-t2a))

# test edge source to sinks
# print('TEST: Unique edge between two nodes: ', num_edges == graph.number_of_edges())
print("TEST: No Source-Sink Edge: ", not graph.has_edge("source_0", "sink_0"))

# freeze graph to prevent further changes
graph = nx.freeze(graph)

#================================== START CPLEX =================================================
#                           Establish Maximization Problem
#================================================================================================

print("Start CPLEX")

c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem


#========================= ADDING VARIABLES AND OBJECTIVE FUNCTION ==============================

print("Adding variables...", end=" ")

# declaring variable types for binary variables
c.variables.add(
    names = flow_var_names,
    types = [ c.variables.type.binary ] * len(flow_var_names)
)

# create variable names
for (source, sink) in all_paths.keys():
    var_portion_of_passengers_inspected = np.append(var_portion_of_passengers_inspected, 'portion_of_({},{})'.format(source, sink))


# Adding the objective function coefficients
c.variables.add(
    names = var_portion_of_passengers_inspected,
    lb = [0] * len(var_portion_of_passengers_inspected),
    ub = [1] * len(var_portion_of_passengers_inspected),
    obj = list(OD.values()),
    types = [ c.variables.type.continuous ] * len(var_portion_of_passengers_inspected)
)

t4 = time.time()
print("Finished! Took {:.5f} seconds".format(t4-t3))

#=================================== CONSTRAINT 6 ===================================================
#                              Mass - Balance Constraint
#================================================================================================
print("Adding Constraint (6) [Mass - Balance Constraint] ...", end=" ")

for k in inspectors:
    for node in graph.nodes():
        if graph.nodes[node]['time_stamp']:

            in_indices = []

            for p in graph.predecessors(node):
                if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k): # not a sink/source
                    in_indices.append('var_x_{}_{}_{}'.format(p, node, k))
            in_vals = [1] * len(in_indices)

            out_indices = []

            for p in graph.successors(node):
                if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k):
                    out_indices.append('var_x_{}_{}_{}'.format(node, p, k))

            out_vals = [-1] * len(out_indices)

            c.linear_constraints.add(
                lin_expr = [cplex.SparsePair(
                                ind = in_indices + out_indices,
                                val = in_vals + out_vals
                            )],
                senses = ['E'],
                rhs = [0],
                names = ['mass_balance_constr_{}_{}'.format(node, k)]
            )

t5 = time.time()

print('Finished! Took {:.5f} seconds'.format(t5-t4))


#=================================== CONSTRAINT 7 ===============================================
#                              Sink and Source Constraint
#================================================================================================

print("Adding constraint (7) [Sink and Source Constraint]...", end=" ")

for k, vals in inspectors.items():
    sink = "sink_" + str(k)
    source = "source_" + str(k)

    c.linear_constraints.add(
        lin_expr = [cplex.SparsePair(
                        ind = ['var_x_{}_{}_{}'.format(u, sink, k) for u in graph.predecessors(sink)],
                        val = [1] * graph.in_degree(sink)
                    )],
        senses = ['E'],
        rhs = [1],
        names = ['sink_constr_{}'.format(k)]
    )

    c.linear_constraints.add(
        lin_expr = [ cplex.SparsePair(
                        ind = ['var_x_{}_{}_{}'.format(source, u, k) for u in graph.successors(source)] ,
                        val = [1] * graph.out_degree(source)
                    )],
        senses = ['E'],
        rhs = [1],
        names = ['source_constr_{}'.format(k)]
    )

t6 = time.time()
print('Finished! Took {:.5f} seconds'.format(t6-t5))


#===================================== CONSTRAINT 8 ==================================================
#                        Time Flow/Number of Working Hours Constraint
#================================================================================================

print("Adding Constraint (8) [Time Flow Constraint]...", end=" ")

for k, vals in inspectors.items():
    source = "source_" + str(k) + ""
    sink = "sink_" + str(k)
    c.linear_constraints.add(
        lin_expr = [cplex.SparsePair(
                    ind = ['var_x_{}_{}_{}'.format(u, sink, k) for u in graph.predecessors(sink)]
                        + ['var_x_{}_{}_{}'.format(source, v, k) for v in graph.successors(source)],
                    val = [time.mktime(parse(graph.nodes[u]['time_stamp']).timetuple())
                                    for u in graph.predecessors(sink)]
                        + [-time.mktime(parse(graph.nodes[v]['time_stamp']).timetuple())
                                    for v in graph.successors(source)]
                        )],
        senses = ['L'],
        rhs = [vals['working_hours'] * HOUR_TO_SECONDS],
        names = ['time_flow_constr_{}'.format(k)]
    )

t7 = time.time()
print("Finished! Took {:.5f} seconds".format(t7-t6))


#================================== CONSTRAINT 9 ==========================================
#                   Minimum Constraint (Linearizing the Objective Function)
#================================================================================================

print('Adding Constraint (9) [Minimum Constraint]...', end = " ")

for (u, v), path in all_paths.items():
    if not ("source_" in u+v or "sink_" in u+v):
        indices = ['portion_of_({},{})'.format(u,v)] + ['var_x_{}_{}_{}'.format(i,j,k) for i,j in zip(path, path[1:]) for k in inspectors]
        values = [1] + [-KAPPA * graph.edges[i,j]['travel_time']/graph.edges[i,j]['num_passengers'] for i,j in zip(path, path[1:]) for k in inspectors]
        c.linear_constraints.add(
            lin_expr = [cplex.SparsePair(ind = indices, val = values)], # needs to be checked
            senses = ['L'],
            rhs = [0],
            # range_values = [0],
            names = ['percentage_inspected_on_({},{})'.format(u, v)]
        )

t8 = time.time()
print("Finished! Took {:.5f} seconds".format(t8-t7))


#================================== POST-PROCESSING ================================================

print('Write to inspectors.lp ...', end=" ")
c.write('inspectors.lp')
t9 =time.time()
print('Finished! Took {:.5f} seconds'.format(t9-t8))

# check for feasibility
print("Problem type: {}".format(c.get_problem_type()))
# problem stats
print("Problem stats: {}".format(c.get_stats()))



print("Now solving ...", end = " ")
c.solve()
# get method
print("Problem method: {}".format(c.solution.get_method()))

print("Solution Status: ", c.solution.get_status())
t10 = time.time()
print('Finished! Took {:.5f} seconds'.format(t10-t9))
print("Print out solutions:")

try:
    res = c.solution.get_values( flow_var_names )
    #print(res)
except cplex.exceptions.errors.CplexSolverError:
    print("No solution exists.")

print("Test: Do 'flow_var_names' and 'res' have same size? ", len(flow_var_names)==len(res))

# post-processing
paths = [re.split('_|\^|@', edge)[2:] for edge, x_val in zip(flow_var_names, res) if x_val]

print("Edges Number = ", len(paths))

#for edge in paths:
    #print(edge)

df_paths = pd.DataFrame(paths, columns=['from_station', 'departure_time', 'to_station', 'arrival_time', 'inspector_id'])

#df_paths['inspector_id'].astype('int8')

for k, vals in inspectors.items():
    print("Solution for Inspector ", k)
    path = df_paths[df_paths['inspector_id'] == str(k)]
    path = path.sort_values(by=['departure_time'])
    print(path.to_string())
    path.to_csv('inspector_0_path.csv', index = False)

#print(len(paths))


t11= time.time()
print("Programme Terminated! Took {:.5f} seconds".format(t11-t1))

# obtain method used in CPLEX
print("CPLEX method used in solver is: {}".format(c.solution.get_method()))
