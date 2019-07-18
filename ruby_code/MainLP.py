# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# @author: Ruby Abrams

import sys

# change local PATH environment for Python
# sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')

import cplex
import networkx as nx
import time
import re
import pandas as pd
from scipy import *
from scipy.sparse import *
import numpy as np
#import Logger  # print out to file
from datetime import datetime, timedelta
from dateutil.parser import parse
import matplotlib.pyplot as plt

from OD_matrix import *

# networkx start
graph = nx.DiGraph() # nx.MultiDiGraph()

inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
              1 : {"base": 'HH', "working_hours": 5, "rate": 10},
              2 : {"base": 'AHAR', "working_hours": 6, "rate": 15}}

flow_var_names = []

# dictionary with keys being var_M and values being upper-bounds
var_passengers_inspected = {}

HOUR_TO_SECONDS = 3600
MINUTE_TO_SECONDS = 60

input_dir = '../hai_code/Mon_Arcs.txt'

#============================= CONSTRUCTING THE GRAPH ============================================

print("Building graph ...", end = " ")
t1 = time.time()

num_edges = 0

with open(input_dir, "r") as f:
    for line in f.readlines()[:-1]:
        line = line.replace('\n','').split(' ')
        start = line[0]+'@'+line[1]
        end = line[2]+'@'+line[3]

        for k in inspectors:
            flow_var_names.append('var_x_{}_{}_{}'.format(start, end, k))

        var_passengers_inspected['var_M_{}_{}'.format(start, end)] = int(line[4])

        graph.add_node(start, station = line[0], time_stamp = line[1])
        graph.add_node(end, station = line[2], time_stamp = line[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))
            num_edges += 1

# time to build graph
t2 = time.time()

print('Finished! Took {:.5f} seconds'.format(t2-t1))

nx.write_gexf(graph, './DiGraph')
print('graph saved')

=======
#================================ OD Estimation ===============================

# create set of all paths traveling through each arc
shortest_paths, arc_paths = create_arc_paths(graph)
# implement the multiproportional algorithm
X = multiproportional(arc_paths)
# generate the OD-matrix disctionary (sparse representation)
nodes = graph.nodes()
nod_idx = {node: i for i,node in enumerate(nodes)}
T = generate_OD_matrix(nod_idx, shortest_paths, arc_paths, X)
# generate new weights vector for number of new passengers departing from each node
N = len(nodes)
new_weights = T*np.ones((N,1))
print(N)
print(new_weights)
quit()

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
            num_edges += 1
            flow_var_names.append('var_x_{}_{}_{}'.format(source, node, k))
            var_passengers_inspected['var_M_{}_{}'.format(source, node)] = 0
            graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
            num_edges += 1
            flow_var_names.append('var_x_{}_{}_{}'.format(node, sink, k))
            var_passengers_inspected['var_M_{}_{}'.format(node, sink)] = 0

t3 = time.time()

print('Finished! Took {:.5f} seconds'.format(t3-t2))

# test edge source to sinks
print('TEST: Unique edge between two nodes: ', num_edges == graph.number_of_edges())
print("TEST: No Source-Sink Edge: ", not graph.has_edge("source_0", "sink_0"))

# freeze graph to prevent further changes
graph = nx.freeze(graph)

print('successors of FFU@10:51:00')

for node in graph.successors('FFU@10:51:00'):
    print(node)



#================================== START CPLEX =================================================

print("Start CPLEX")

c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem


#========================= ADDING VARIABLES AND OBJECTIVE FUNCTION ==============================

print("Adding variables...", end=" ")

# adding objective function and declaring variable types
c.variables.add(
    names = flow_var_names,
    types = [ c.variables.type.binary ] * len(flow_var_names)
)


c.variables.add(
    names = list(var_passengers_inspected.keys()),
    lb = [0] * len(var_passengers_inspected),
    ub = list(var_passengers_inspected.values()),
    obj = [1] * len(var_passengers_inspected),
    types = [ c.variables.type.continuous ] * len(var_passengers_inspected))


t4 = time.time()
print("Finished! Took {:.5f} seconds".format(t4-t3))


#================================== CONSTRAINT 9 ==========================================

print('Adding Constraint (9)...', end = " ")

for u, v in graph.edges():
    if not ("source_" in u+v or "sink_" in u+v):
        indices = ['var_M_{}_{}'.format(u,v)] + ['var_x_{}_{}_{}'.format(u,v,k) for k in inspectors]
        values = [1] + [-vals["rate"] * graph.edges[u,v]['travel_time'] for k, vals in inspectors.items()]
        c.linear_constraints.add(
            lin_expr = [cplex.SparsePair(ind = indices, val = values)], # needs to be checked
            senses = ['L'],
            rhs = [0],
            range_values = [0],
            names = ['bdd_by_inspector_count_{}_{}'.format(u, v)]
        )

t5 = time.time()

print('Finished! Took {:.5f} seconds'.format(t5-t4))


#=================================== CONSTRAINT 7 ===============================================

print("Adding constraint (7) ...", end=" ")

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

print("Adding Constraint (8)...", end=" ")

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


#=================================== CONSTRAINT 6 ===================================================

print("Adding Constraint (6)...", end=" ")

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


t8 = time.time()

print("Finished! Took {:.5f} seconds".format(t8-t7))


#================================== POST-PROCESSING ================================================

print('Write to inspectors.lp ...', end=" ")
c.write('inspectors.lp')
t9 =time.time()
print('Finished! Took {:.5f} seconds'.format(t9-t8))


print("Now solving ...", end = " ")
c.solve()
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
    #source = 'source_' + str(k)
    #sink = 'sink_' + str(k)
    path = df_paths[df_paths['inspector_id'] == str(k)]
    path = path.sort_values(by=['departure_time'])
    print(path.to_string())
    path.to_csv('inspector_0_path.csv', index = False)

#print(len(paths))


t11= time.time()
print("Programme Terminated! Took {:.5f} seconds".format(t11-t1))

#print(flow_var_names[:10])
