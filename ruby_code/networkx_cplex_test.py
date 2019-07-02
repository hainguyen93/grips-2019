
import sys
import networkx as nx
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')
import cplex

# networkx start
graph = nx.DiGraph()
graph.add_edge(0, 1, num_passengers=7.2, inspector=False, time =2, num_passengers_checked = 0)
graph.add_edge(1, 2, num_passengers=-2, inspector=True, time=3, num_passengers_checked = 0)
graph.add_edge(1, 6, num_passengers=0.5, inspector = False, time = 4, num_passengers_checked = 0)
graph.add_node(3, name='ZIB')
graph.node[1]['name'] = 'foo'
# example code to add an edge to the digraph
# graph.add_edge(start_node, end_node, num_passengers, travel_time)

sinks = []
sources = []
# will need subgraphs to know which nodes are sinks/sources
# need to label cetain nodes as sinks and sources
# if is_sink:
#     graph.node[index]['name'] = 'sink'
#     sinks.append(node)
# elif is_source:
#     graph.node[index]['name'] = 'source'
#     sources.append(node)

# when creating the Digraph

number_of_inspectors = 10 # len(sinks)
# the number of source and sink nodes will determine the number of inspectors
inspectors = range(number_of_inspectors)


print(graph.nodes())
for u, v in graph.edges():
    if 'GRIPS' in graph[u][v] and graph[u][v]['GRIPS']:
        print(graph[u][v])


# cplex start
c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem

# add variables: x, w, t
c.variables.add(names=['M','x','w','t'], types=['I','B', 'I', 'C'])

flow_var_names = [] # adding variable names to each edge
for k in inspectors:
    for u, v in graph.edges():
        var_name = 'var_M_{}_{}'.format(u, v)
        flow_var_names.append(var_name)
        var_name = 'var_x_{}_{}^{}'.format(u, v, k)
        flow_var_names.append(var_name)
        var_name = 'var_w_{}_{}'.format(u, v)
        flow_var_names.append(var_name)
        var_name = 'var_t_{}_{}'.format(u, v)
        flow_var_names.append(var_name)

# upper bound on number of output coefficients:
#    number of edges * number of inspectors
# the objective function coefficients using the weights of the graph
obj = [graph[u][v]['num_passengers'] for u, v in graph.edges()]
obj = obj+[graph[u][v]['time'] for u, v in graph.edges()]
obj = obj+[graph[u][v]['inspector'] for u, v in graph.edges()]
obj = obj+[graph[u][v]['num_passengers_checked'] for u, v in graph.edges()]
c.variables.add(names=flow_var_names, lb=[0]*len(flow_var_names), obj=obj)

var_name_to_id = {}
for i, var_name in enumerate(c.variables.get_names()):
    var_name_to_id[var_name] = i

print(var_name_to_id)

# add constraints
lin_expr = []
names = []
rhs = []
# ================ minimization constraint ====================
# adding bounded constraint 1
for u,v in graph.edges():
    c.linear_constraints.add(
        lin_expr = var_name_to_id['var_M_{}_{}'.format(u,v)],
        senses = ['L'],
        rhs = var_name_to_id['var_w_{}_{}'.format(u,v)],
        range_values = [0],
        names = 'bdd_by_train_capacity_{}_{}'.format(u,v)
    )
# adding bounded constraint 2
lin_expr = []
names = []
rhs = []
kappa = 5 # rate at which inspector checks passengers. For example: 5 pass/hour
for u,v in graph.edges():
    # max number of inspected passengers bounded by number of inspectors
    # aboard each train ride
    total = sum([kappa*var_name_to_id['var_x_{}_{}^{}'.format(u,v,k)]*\
    var_name_to_id['var_t_{}_{}'.format(u,v)] for k in inspectors])
    c.linear_constraints.add(
        lin_expr = var_name_to_id['var_M_{}_{}'.format(u,v)],
        senses = ['L'],
        rhs = total,
        range_values = [0],
        names = 'bdd_by_inspector_count_{}_{}'.format(u,v)
    )

# ==================== time flow constraint ==================
lin_expr = []
names = []
rhs = []
# find all predecessors of sink node k, sum over it
# edge constraint for sinks
for k in inspectors:
    indices = []
    for u in sinks.predecessors(sinks[k]):
        indices.append(var_name_to_id['var_x_{}_{}^{}'.format(u,sinks[k],k)])
    values = [1]*len(indices)
    lin_expr.append(cplex.SparsePair(ind=indices, val=values))
    names.append('flow_into_sink_{}'.format(k))
num = len(names)
c.linear_constraints.add(lin_expr=lin_expr, senses= num*['E'], rhs=num*[1], names=names)

lin_expr = []
names = []
rhs = []
# edge constraint for sources
for k in inspectors:
    indices = []
    for v in sinks.successors(sources[k]):
        indices.append(var_name_to_id['var_x_{}_{}^{}'.format(sources[k],v)])
    values = [1]*len(indices)
    lin_expr.append(cplex.SparsePair(ind=indices, val=values))
    names.append('flow_out_of_source_{}'.format(k))
num = len(names)
c.linear_constraints.add(lin_expr=lin_expr, senses= num*['E'], rhs=num*[1], names=names)

# ===================== mass-balance constraint =================
lin_expr = []
names = []
rhs = []
# note: need to account for super sources and super sinks
for v in graph.nodes():
    indices = []
    # look at all predecessors u of node v
    for u in graph.predecessors(v):
        indices.append(var_name_to_id['var_x_{}_{}^{}'.format(u, v)])
    values = [1] * len(indices)
    # look at all successors w of node v
    for w in graph.successors(v):
        indices.append(var_name_to_id['var_x_{}_{}^{}'.format(v, w)])
        values.append(-1)
    lin_expr.append(cplex.SparsePair(ind=indices, val=values))
    names.append('constr_flow_conservation_{}'.format(v))
num = len(names)
c.linear_constraints.add(lin_expr=lin_expr, senses=num*['E'], rhs=num*[0], names=names)

c.write('test.lp')
c.solve()

vals = c.solution.get_values( [var_name_to_id[var_name] for var_name in flow_var_names] )
print(vals)
