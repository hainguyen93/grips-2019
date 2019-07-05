# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# Author: Ruby Abrams
import sys
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')
import cplex
import networkx as nx
import time
from datetime import datetime, timedelta
from dateutil import parser

# networkx start
graph = nx.MultiDiGraph() # nx.MultiDiGraph()

inspectors = { 0:{"base": 'RDRM', "theta": 8*60, "rate": 12}} # for now

# start time
t1 = time.time()

flow_var_names = []
number_of_passengers_checked_M = []
num_edges = 0
count = 0
with open('../data/digraph_data', "r") as file:
    for line in file.readlines()[:-1]:
        line = line.replace('\n','').split(' ')
        start = line[0]+'@'+line[1]
        end = line[2]+'@'+line[3]
        for k in inspectors:
            flow_var_names.append('var_x_{}_{}^{}'.format(start, end, k))
        number_of_passengers_checked_M.append('var_M_{}_{}'.format(start, end))
        graph.add_node(start, station = line[0], time_stamp = line[1])
        graph.add_node(end, station = line[2], time_stamp = line[3])
        # we assume unique edges between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end,
                    num_passengers= int(line[4]),
                    travel_time =int(line[5])
            )
            num_edges+=1

print('built graph')

# time to build graph
t2 = time.time()
print("Build graph took {} seconds".format(t2-t1))

# print("Num of edges checked: {}".format(num_edges ==  graph.number_of_edges()))
g = graph.nodes()

# adding sources and sinks to DiGraph
for k, vals in inspectors.items():
    source = "source_" + str(k)
    sink = "sink_"+str(k)
    graph.add_node(source, station = vals['base'], time_stamp = None)
    graph.add_node(sink, station = vals['base'], time_stamp = None)
    for node in graph.nodes():
        if g[node]['station'] == vals['base'] and not g[node]['time_stamp']:
            # adding edge between sink and events and adding to the variable dictionary
            graph.add_edge(source, node, num_passengers = 0, travel_time = 0)
            flow_var_names.append('var_x_{}_{}^{}'.format(source, node, k))
            graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
            flow_var_names.append('var_x_{}_{}^{}'.format(node, sink, k))

print('added source and sink')

t3 = time.time()
print("Adding Souce/sink took {} seconds".format(t3-t2))
# save the digraph
# nx.write_gexf(graph, "event_digraph.gexf")

# print('saved digraph')


# cplex start
c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem

# adding objective function and declaring variable types
c.variables.add(
    names=number_of_passengers_checked_M,
    lb=[0]*len(number_of_passengers_checked_M),
    obj=[1]*len(number_of_passengers_checked_M),
    types=['C' for _ in range(len(number_of_passengers_checked_M))]
)
c.variables.add(
    names=flow_var_names,
    types=['B' for _ in range(len(flow_var_names))]
)

# ================ minimization constraint ====================
# start adding linear constraints for each edge
# adding bounded constraint 1 (equation 10)
for u, v in graph.edges():
    if not ("sink" in u+v or "source" in u+v):
        c.linear_constraints.add(
            lin_expr = [cplex.SparsePair(ind=['var_M_{}_{}'.format(u, v)], val=[1])], # needs to be checked
            senses = ['L'],
            rhs = [graph[u][v][0]['num_passengers']],
            range_values = [0],
            names = ['bdd_by_num_passengers_{}_{}'.format(u, v)]
        )
        # adding bounded constraint 2 (equation 9)
        index = ['var_M_{}_{}'.format(u, v)]+['var_x_{}_{}^{}'.format(u, v, k) for k in inspectors]
        values = [1]+[-vals["theta"]*graph[u][v][0]['travel_time'] for k, vals in inspectors.items()]
        c.linear_constraints.add(
            lin_expr = [cplex.SparsePair(ind=index, val=values)], # needs to be checked
            senses = ['L'],
            rhs = [0],
            range_values = [0],
            names = ['bdd_by_inspector_count_{}_{}'.format(u, v)]
        )
print('contr1 finished')
# ================================================================
#           Time flow and sink/source node constraint
# ================================================================
# (equation 8) and (equation 7)

lin_expr_time_flow = []
names = []

lin_expr_sink_constr = []
names_2 = []

lin_expr_source_constr = []
names_3 = []

for k, vals in inspectors.items():
    indices_source = []
    indices_sink = [] # for sinks
    # look at all predecessors of sink k
    sink = "sink_"+str(k)
    values = []
    for u in graph.predecessors(sink):
        indices_sink.append('var_x_{}_{}^{}'.format(u,sink, k))
        values.append(parser(graph[u]["time_stamp"]).seconds)
    # look at all successors of source k
    source = "source_"+str(k)
    for v in graph.successors(source):
        indices_source.append('var_x_{}_{}^{}'.format(source, v, k))
        values.append(-parser(graph[v]['time_stamp']).seconds)
    # add time flow constraint
    lin_expr_time_flow.append(cplex.SparsePair(ind = indices_sink+indices_source, val= values))
    # add sink node constraint
    lin_expr_sink_constr.append(cplex.SparsePair(ind = indices_sink, val= [1]*graph.in_degree(sink)))
    # add source node constraint
    lin_expr_source_constr.append(cplex.SparsePair(ind = indices_source, val= [1]*graph.out_degree(source)))
    names.append('time_flow_constr_{}'.format(k))
    names_2.append('sink_constr_{}'.format(k))
    names_3.append('source_constr_{}'.format(k))
    c.linear_constraints.add(
        lin_expr = lin_expr_time_flow,
        senses=['L'],
        rhs=[vals["theta"]],
        names=names
    )
    c.linear_constraints.add(
        lin_expr = lin_expr_sink_constr,
        senses=['E'],
        rhs=[1],
        names=names_2
    )
    c.linear_constraints.add(
        lin_expr=lin_expr_source_constr,
        senses=['E'],
        rhs=[1],
        names=names_3
    )
print('constr2 finished')
# ===================== mass-balance constraint =================
lin_expr = []
names = []
rhs = []
for q in graph.nodes():
    if not "sink" in q and not "source" in q:
        # grab all successors and predecessors of every node and dot them
        incoming_indices = ['var_x_{}_{}^{}'.format(p, q, k) for p in graph.predecessors(q) for k in inspectors]
        values = [1]*len(incoming_indices)
        outgoing_indices = ['var_x_{}_{}^{}'.format(q, p, k) for p in graph.successors(q) for k in inspectors]
        values = values + [-1]*len(outgoing_indices)
        lin_expr.append(cplex.SparsePair(ind = incoming_indices+outgoing_indices, val = values))
        names.append('mass_balance_constr_{}'.format(q))
        c.linear_constraints.add(
            lin_expr = lin_expr,
            senses = ['E'],
            rhs = [0],
            names = names
        )
print('constr3 finished')
c.write('inspectors.lp')
print('written. Now solving...')
c.solve()
print('solved')
vals = c.solution.get_values( flow_var_names )
print(vals)
