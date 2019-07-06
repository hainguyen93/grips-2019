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

# networkx start
graph = nx.DiGraph() # nx.MultiDiGraph()

inspectors = { 0 : {"base": 'RDRM', "working_hours": 8*60, "rate": 12}} # for now

flow_var_names = []

# dictionary with keys being var_M and values being upper-bounds
var_passengers_inspected = {}

HOUR_TO_SECONDS = 3600

#num_edges = 0
#count = 0

input_dir = '/home/optimi/bzfnguye/grips-2019/hai_code/Mon_Arcs.txt'

print("Building graph ...", end = " ")
t1 = time.time()

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
            #num_edges+=1

# time to build graph
t2 = time.time()

print('Finished!. ', end=" ")
print("Took {} seconds".format(t2-t1))

#print("Num of edges checked: {}".format(num_edges ==  graph.number_of_edges()))
#g = graph.nodes()  # iterator over nodes

print("Adding Sinks/Sources...", end=" ")

# adding sources and sinks to DiGraph
for k, vals in inspectors.items():
    source = "source_" + str(k)
    sink = "sink_"+str(k)
    graph.add_node(source, station = vals['base'], time_stamp = None)
    graph.add_node(sink, station = vals['base'], time_stamp = None)
    for node in graph.nodes():
        if graph.nodes[node]['station'] == vals['base'] and not graph.nodes[node]['time_stamp']:
            
            # adding edge between sink and events and adding to the variable dictionary
            graph.add_edge(source, node, num_passengers = 0, travel_time = 0)
            flow_var_names.append('var_x_{}_{}^{}'.format(source, node, k))
            var_passengers_inspected['var_M_{}_{}'.format(source, node)] = 0
            graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
            flow_var_names.append('var_x_{}_{}^{}'.format(node, sink, k))
            var_passengers_inspected['var_M_{}_{}'.format(node, sink)] = 0

t3 = time.time()

print('Finished! ', end=" ")
print("Took {} seconds".format(t3-t2))

# freeze graph to prevent further changes
graph = nx.freeze(graph)

# save the digraph
# nx.write_gexf(graph, "event_digraph.gexf")

# print('saved digraph')


# cplex start
print("Start CPLEX")

c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem

print("Adding variables...", end=" ")

# adding objective function and declaring variable types
c.variables.add(
    names = var_passengers_inspected.keys(),
    lb = [0]*len(var_passengers_inspected),
    ub = var_passengers_inspected.values(),
    obj = [1]*len(var_passengers_inspected),
    types = [ c.variables.type.continuous ]*len(var_passengers_inspected)
)

c.variables.add(
    names = flow_var_names,
    types = [ c.variables.type.binary ] * len(flow_var_names)
)

t4 = time.time()
 
print("Finished!", end = " ")
print("Took {} seconds".format(t4-t3))

# ================ minimization constraint ====================
# start adding linear constraints for each edge
# adding bounded constraint 1 (equation 10)

print('Adding Constraint (9)...', end = " ")

for u, v in graph.edges():
    #if not ("sink" in u+v or "source" in u+v):
        #c.linear_constraints.add(
            #lin_expr = [cplex.SparsePair(ind=['var_M_{}_{}'.format(u, v)], val=[1])], # needs to be checked
            #senses = ['L'],
            #rhs = [graph[u][v][0]['num_passengers']],
            #range_values = [0],
            #names = ['bdd_by_num_passengers_{}_{}'.format(u, v)]
        #)
        # adding bounded constraint 2 (equation 9)
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

print('Finished!', end = " ")
print("Took {} seconds".format(t5-t4))


# ================================================================
#           Time flow and sink/source node constraint
# ================================================================
# (equation 8) and (equation 7)

#lin_expr_time_flow = []
#names = []

#lin_expr_sink_constr = []
#names_2 = []

#lin_expr_source_constr = []
#names_3 = []

# Adding Constraint (7)
print("Adding constraint (7) ...", end=" ")

for k, vals in inspectors.items():
    #indices_source = []
    #indices_sink = [] # for sinks
    # look at all predecessors of sink k    
    
    sink = "sink_" + str(k)
    source = "source_" + str(k)
    
    #values = []
    #for u in graph.predecessors(sink):
    #    indices_sink.append('var_x_{}_{}^{}'.format(u,sink, k))
    #    values.append(parser(graph[u]["time_stamp"]).seconds)
        
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
    
    # look at all successors of source k
    #source = "source_"+str(k)
    #for v in graph.successors(source):
        #indices_source.append('var_x_{}_{}^{}'.format(source, v, k))
        #values.append(-parser(graph[v]['time_stamp']).seconds)
    # add time flow constraint
    #lin_expr_time_flow.append(cplex.SparsePair(ind = indices_sink+indices_source, val= values))
    ## add sink node constraint
    ##lin_expr_sink_constr.append(cplex.SparsePair(ind = indices_sink, val= [1]*graph.in_degree(sink)))
    ## add source node constraint
    ##lin_expr_source_constr.append(cplex.SparsePair(ind = indices_source, val= [1]*graph.out_degree(source)))
    #names.append('time_flow_constr_{}'.format(k))
    ##names_2.append('sink_constr_{}'.format(k))
    ##names_3.append('source_constr_{}'.format(k))
    #c.linear_constraints.add(
        #lin_expr = lin_expr_time_flow,
        #senses=['L'],
        #rhs=[vals["working_hours"]],
        #names=names
    #)
    #c.linear_constraints.add(
        #lin_expr = lin_expr_sink_constr,
        #senses=['E'],
        #rhs=[1],
        #names=names_2
    #)
    #c.linear_constraints.add(
        #lin_expr=lin_expr_source_constr,
        #senses=['E'],
        #rhs=[1],
        #names=names_3
    #)
    
    
t6 = time.time()
print('Finished!', end = " ")
print("Took {} seconds".format(t6-t5))

# Adding Constraint (8)
print("Adding Constraint (8)...", end=" ")

for k, vals in inspectors.items():
    source = "source_" + str(k)
    sink = "sink_" + str(k)
    c.linear_constraints.add(
        lin_expr = [cplex.SparsePair(
                    ind = ['var_x_{}_{}^{}'.format(u, sink, k) for u in graph.predecessors(sink)]
                        + ['var_x_{}_{}^{}'.format(source, v, k) for v in graph.successors(source)],
                    val = [parse(graph.nodes[u]['time_stamp']).seconds for u in graph.predecessors(sink)]
                        + [-parse(graph.nodes[v]['time_stamp']).seconds for v in graph.successors(source)]
                        )],
        senses = ['L'],
        rhs = [vals['working_hours'] * HOUR_TO_SECONDS],
        names = ['time_flow_constr_{}'.format(k)]
    )
        
        
t7 = time.time()
print("Finished!", end=" ")
print("Took {} seconds".format(t7-t6))


# ===================== mass-balance constraint =================
#lin_expr = []
#names = []
#rhs = []

# Adding Constraint (6)
print("Adding Constraint (6)...", end=" ")

for node in graph.nodes():
    if not graph.nodes[node]['time_stamp']:
    #if (not "sink" in node) and (not "source" in node):
        # grab all successors and predecessors of every node and dot them
        in_indices = ['var_x_{}_{}^{}'.format(p, node, k) 
                                    for p in graph.predecessors(node) for k in inspectors]
        in_vals = [1] * len(in_indices)
        
        out_indices = ['var_x_{}_{}^{}'.format(node, p, k) 
                                    for p in graph.successors(node) for k in inspectors]
        out_vals = [-1] * len(out_indices)
        
        #lin_expr.append(cplex.SparsePair(ind = incoming_indices+outgoing_indices, val = values))
        #names.append('mass_balance_constr_{}'.format(q))
        c.linear_constraints.add(
            lin_expr = [cplex.SparsePair(
                            ind = in_indices + out_indices,
                            val = in_vals + out_vals
                        )],
            senses = ['E'],
            rhs = [0],
            names = 'mass_balance_constr_{}'.format(node)
        )
        
        
t8 = time.time()

print("Finished!", end = " ")
print("Took {} seconds".format(t8-t7))


#print('constr3 finished')
print('Write to inspectors.lp ...', end=" ")
c.write('inspectors.lp')
print('Finished!', end=" ")
t9 =time.time()
print("Took {} seconds".format(t9-t8))


print("Now solving ...", end = " ")
c.solve()
t10 = time.time()
print('Finished!', end=" ")
print("Took {} seconds".format(t10-t9))

print("Print out solutions:")
vals = c.solution.get_values( flow_var_names )
print(vals)

t11= time.time()
print("Programme Terminated!", end= " ")
print("Took {} seconds".format(t11-t1))
