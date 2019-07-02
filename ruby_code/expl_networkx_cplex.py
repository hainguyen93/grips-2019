
import sys

import networkx as nx
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')
import cplex

# networkx start
graph = nx.DiGraph()
graph.add_edge(0, 1, weight=7.2, GRIPS=False)
graph.add_edge(1, 2, weight=-2, GRIPS=True)
graph.add_edge(1, 6, weight=0.5)
graph.add_node(3, name='ZIB')
graph.node[1]['name'] = 'foo'

print(graph.nodes())
for u, v in graph.edges():
    if 'GRIPS' in graph[u][v] and graph[u][v]['GRIPS']:
        print(graph[u][v])




# cplex start
c = cplex.Cplex()
c.set_problem_type(c.problem_type.LP)
c.objective.set_sense(c.objective.sense.maximize)

# add variables
c.variables.add(names=['var_capacity', 'var_foo'], types=['I', 'B'])
flow_var_names = []
for u, v in graph.edges():
    var_name = 'var_x_{}_{}'.format(u, v)
    flow_var_names.append(var_name)
obj = [graph[u][v]['weight'] for u, v in graph.edges()]
c.variables.add(names=flow_var_names, lb=[0]*len(flow_var_names), obj=obj)

var_name_to_id = {}
for i, var_name in enumerate(c.variables.get_names()):
    var_name_to_id[var_name] = i

print(var_name_to_id)

# add constraints
lin_expr = []
names = []
for v in graph.nodes():
    indices = []
    for u in graph.predecessors(v):
        indices.append(var_name_to_id['var_x_{}_{}'.format(u, v)])
    values = [1] * len(indices)
    for w in graph.successors(v):
        indices.append(var_name_to_id['var_x_{}_{}'.format(v, w)])
        values.append(-1)
    lin_expr.append(cplex.SparsePair(ind=indices, val=values))
    names.append('constr_flow_conservation_{}'.format(v))
num = len(names)
c.linear_constraints.add(lin_expr=lin_expr, senses=num*['E'], rhs=num*[0], names=names)

c.write('test.lp')
c.solve()

vals = c.solution.get_values( [var_name_to_id[var_name] for var_name in flow_var_names] )
print(vals)

