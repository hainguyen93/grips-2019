# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# Author: Ruby Abrams
import sys
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')
import cplex
import networkx as nx

# networkx start
graph = nx.DiGraph()

inspectors = { 0:{"base": 'RDRM', "theta": 8*60, "rate": 12}} # for now

flow_var_names = []
number_of_passengers_checked_M = []

with open('../Data/digraph_data', "r") as file:
    for line in file.readlines()[:-1]:
        line = line.replace('\n','').split(' ')

        start = line[0]+'@'+line[1]
        end = line[2]+'@'+line[3]

        for k in inspectors:
            flow_var_names.append('var_x_{}_{}^{}'.format(start, end, k))
        num_passengers_checked_M.append('var_M_{}_{}'.format(start, end))
        graph.add_node(start, station = line[0], time_stamp = line[1])
        graph.add_node(end, station = line[2], time_stamp = line[3])
        graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))

# adding sources and sinks to DiGraph
for k, vals in inspectors.items():
    source = "source_" + str(k)
    sink = "sink_"+str(k)
    graph.add_node(source, time_stamp = null)
    graph.add_node(sink, time_stamp = null)
    for node in graph.nodes():
        if node.station is vals['base'] and node.time_stamp is not null:
            graph.add_edge(graph[source], node, num_passengers = 0, travel_time = 0)
            graph.add_edge(node, graph[sink], num_passengers=0, travel_time = 0 )

# nx.write_gexf(graph, "event_digraph.gexf")
# cplex start
c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem

# add variables: M, x, w, t
c.variables.add(names=['M','x','w','t'], types=['I','B', 'I', 'C'])

# adding objective function
c.variables.add(names=num_passengers_checked_M, lb=[0]*len(num_passengers_checked_M), obj=[1]*num_edges)

# ================ minimization constraint ====================
# start adding linear constraints for each edge
# adding bounded constraint 1 (equation 10)
for u, v in graph.edges():
    c.linear_constraints.add(
        lin_expr = [cplex.SparsePair(ind=['var_M_{}_{}'.format(u, v)], val=[1])], # needs to be checked
        senses = ['L'],
        rhs = [graph[u][v]['num_passengers']],
        range_values = [0],
        names = 'bdd_by_num_passengers_{}_{}'.format(u, v)
    )
    # adding bounded constraint 2 (equation 9)
    c.linear_constraints.add(
        lin_expr = [cplex.SparsePair(ind=['var_M_{}_{}'.format(u, v)], val=[1])], # needs to be checked
        senses = ['L'],
        rhs = [cplex.SparsePair(ind=['var_x_{}_{}^{}'.format(u, v, k) for k in inspectors],
                                val=[vals["theta"]*var_name_to_id['var_t_{}_{}'.format(u, v) for _, vals in inspectors.items()])],
        range_values = [0],
        names = 'bdd_by_inspector_count_{}_{}'.format(u, v)
    )
# ================================================================
#           Time flow and sink/source node constraint
# ================================================================
# (equation 8) and (equation 7)

lin_expr_time_flow = []
names = []
rhs = []

lin_expr_sink_constr = []
names_2 = []
rhs_2 = []

lin_expr_source_constr = []
names_3 = []
rhs_3 = []


for k, vals in inspectors.items():
    indices = []
    indices_2 = [] # for sinks
    indices_3 = [] # for sources
    # look at all predecessors of sink k
    sink = "sink_"+str(k)
    for u in graph.predecessors(sink):
        indices.append(var_name_to_id['var_x_{}_{}^{}'.format(u,sink, k)]*u.time_stamp)
        indices_2.append(var_name_to_id['var_x_{}_{}^{}'.format(u, sink, k)])
    values = [1]*len(indices)
    values_2 = [1]*len(indices_2)
    # look at all successors of source k
    source = "source_"+str(k)
    for v in graph.successors(source):
        indices.append(var_name_to_id['var_x_{}_{}^{}'.format(source, v, k)]*u.time_stamp)
        values.append(-1)
        indices_3.append(var_name_to_id['var_x_{}_{}^{}'.format(source, v, k)])
    values_3 = [1]*len(indices_3)
    # add time flow constraint
    lin_expr_time_flow.append(cplex.SparsePair(ind = indices, val= values))
    # add sink node constraint
    lin_expr_sink_constr.append(cplex.SparsePair(ind = indices_2, val= values_2))
    # add source node constraint
    lin_expr_source_constr.append(cplex.SparsePair(ind = indices_3, val= values_3))
    names.append('time_flow_constr_{}'.format(k))
    names_2.append('sink_constr_{}'.format(k))
    names_3.append('source_constr_{}'.format(k))
    c.linear_constraints.add(
        lin_expr = lin_expr_time_flow,
        senses=['L'],
        rhs=[vals["theta"]]],
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

# ===================== mass-balance constraint =================

# note: need to omit sinks and sources
for q in graph.nodes():
    pass
