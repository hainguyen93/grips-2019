# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# @author: Ruby Abrams, Hai Nguyen

import sys

# change local PATH environment for Python
# sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')

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

from tools import *

# networkx start
graph = nx.DiGraph() # nx.MultiDiGraph()

inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
              1 : {"base": 'HH', "working_hours": 5, "rate": 10},
              2 : {"base": 'AHAR', "working_hours": 6, "rate": 15}}

flow_var_names = []

# dictionary with keys being var_M and values being upper-bounds
var_passengers_inspected = {}



input_dir = '../hai_code/Mon_Arcs.txt' # /home/optimi/bzfnguye/grips-2019

#============================= CONSTRUCTING THE GRAPH ============================================

print("Building graph ...", end = " ")
t1 = time.time()

build_graph(input_dir, graph, inspectors, flow_var_names, var_passengers_inspected)

# time to build graph
t2 = time.time()

print('Finished! Took {:.5f} seconds'.format(t2-t1))

#================================ OD Estimation ===============================
print("Estimating OD Matrix ...", end = " ")

T, new_weights = OD_estimation(graph)

t2a = time.time()
print(new_weights)
print('Finished! Took {:.5f} seconds'.format(t2a-t2))

#============================== ADDING SOURCE/SINK NODES ==========================================

print("Adding Sinks/Sources...", end=" ")

add_sources_and_sinks(graph, inspectors, flow_var_names, var_passengers_inspected)

t3 = time.time()

print('Finished! Took {:.5f} seconds'.format(t3-t2a))

# test edge source to sinks
# print('TEST: Unique edge between two nodes: ', num_edges == graph.number_of_edges())
print("TEST: No Source-Sink Edge: ", not graph.has_edge("source_0", "sink_0"))

# freeze graph to prevent further changes
graph = nx.freeze(graph)

print('successors of FFU@10:51:00')

for node in graph.successors('FFU@10:51:00'):
    print(node)

#================================== START CPLEX =================================================

print("Start CPLEX")

c = cplex.Cplex()

start_cplex(c, flow_var_names, var_passengers_inspected, arc_paths)

t4 = time.time()
print("Finished! Took {:.5f} seconds".format(t4-t3))

#=================================== CONSTRAINT 6 ===================================================

print("Adding Constraint (6)...", end=" ")

constr_mass_balance(c, graph, inspectors)

t5 = time.time()

print('Finished! Took {:.5f} seconds'.format(t5-t4))


#=================================== CONSTRAINT 7 ===============================================

print("Adding constraint (7) ...", end=" ")

constr_sink_source(c, graph, inspectors)

t6 = time.time()
print('Finished! Took {:.5f} seconds'.format(t6-t5))


#===================================== CONSTRAINT 8 ==================================================

print("Adding Constraint (8)...", end=" ")

constr_working_hours(c, graph, inspectors)

t7 = time.time()
print("Finished! Took {:.5f} seconds".format(t7-t6))


#================================== CONSTRAINT 9 ==========================================

print('Adding Constraint (9)...', end = " ")

# new constraint
constr_reformulated(c, graph, inspectors, arc_paths)
# old constraint
# constraint_9(c, graph, inspectors)

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
