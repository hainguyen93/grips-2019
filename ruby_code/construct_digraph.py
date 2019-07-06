# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# @author: Ruby Abrams

import sys

# change local PATH environment for Python
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')

import cplex
import networkx as nx
import time
from datetime import datetime, timedelta
from dateutil.parser import parse
import matplotlib.pyplot as plt

# networkx start
graph = nx.DiGraph() # nx.MultiDiGraph()

inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12}} # for now

flow_var_names = []

# dictionary with keys being var_M and values being upper-bounds
var_passengers_inspected = {}

HOUR_TO_SECONDS = 3600
MINUTE_TO_SECONDS = 60

input_dir = '/home/optimi/bzfnguye/grips-2019/hai_code/Mon_Arcs.txt'


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
            flow_var_names.append('var_x_{}_{}^{}'.format(start, end, k))
        
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
            flow_var_names.append('var_x_{}_{}^{}'.format(source, node, k))
            var_passengers_inspected['var_M_{}_{}'.format(source, node)] = 0
            graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
            num_edges += 1
            flow_var_names.append('var_x_{}_{}^{}'.format(node, sink, k))
            var_passengers_inspected['var_M_{}_{}'.format(node, sink)] = 0

t3 = time.time()

print('Finished! Took {:.5f} seconds'.format(t3-t2))

# test edge source to sinks
print('TEST: Unique edge between two nodes: ', num_edges == graph.number_of_edges())
print("TEST: No Source-Sink Edge: ", not graph.has_edge("source_0", "sink_0"))

# freeze graph to prevent further changes
graph = nx.freeze(graph)


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
    indices = ['var_M_{}_{}'.format(u,v)] + ['var_x_{}_{}^{}'.format(u,v,k) for k in inspectors]
    values = [1] + [-vals["working_hours"] * graph.edges[u,v]['travel_time'] for k, vals in inspectors.items()]
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
                        ind = ['var_x_{}_{}^{}'.format(u, sink, k) for u in graph.predecessors(sink)],
                        val = [1] * graph.in_degree(sink)
                    )],
        senses = ['E'],
        rhs = [1],
        names = ['sink_constr_{}'.format(k)]
    )
        
    c.linear_constraints.add(
        lin_expr = [ cplex.SparsePair(
                        ind = ['var_x_{}_{}^{}'.format(source, u, k) for u in graph.successors(source)] ,
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
    source = "source_" + str(k)
    sink = "sink_" + str(k)
    c.linear_constraints.add(
        lin_expr = [cplex.SparsePair(
                    ind = ['var_x_{}_{}^{}'.format(u, sink, k) for u in graph.predecessors(sink)]
                        + ['var_x_{}_{}^{}'.format(source, v, k) for v in graph.successors(source)],
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

for node in graph.nodes():
    if not graph.nodes[node]['time_stamp']:
        in_indices = ['var_x_{}_{}^{}'.format(p, node, k) 
                                    for p in graph.predecessors(node) for k in inspectors]
        in_vals = [1] * len(in_indices)
        
        out_indices = ['var_x_{}_{}^{}'.format(node, p, k) 
                                    for p in graph.successors(node) for k in inspectors]
        out_vals = [-1] * len(out_indices)
        
        c.linear_constraints.add(
            lin_expr = [cplex.SparsePair(
                            ind = in_indices + out_indices,
                            val = in_vals + out_vals
                        )],
            senses = ['E'],
            rhs = [0],
            names = ['mass_balance_constr_{}'.format(node)]
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
t10 = time.time()
print('Finished! Took {:.5f} seconds'.format(t10-t9))
print("Print out solutions:")

try: 
    vals = c.solution.get_values( flow_var_names )
    print(vals)
except cplex.exceptions.errors.CplexSolverError:
    print("No solution exists.")


t11= time.time()
print("Programme Terminated! Took {:.5f} seconds".format(t11-t1))
