
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

from OD_matrix import *



# def build_graph(input_dir, graph, inspectors, flow_var_names, var_passengers_inspected):
#     num_edges = 0
#     with open(input_dir, "r") as f:
#         for line in f.readlines()[:-1]:
#             line = line.replace('\n','').split(' ')
#             start = line[0]+'@'+line[1]
#             end = line[2]+'@'+line[3]
#
#             for k in inspectors:
#                 flow_var_names.append('var_x_{}_{}_{}'.format(start, end, k))
#
#             var_passengers_inspected['var_M_{}_{}'.format(start, end)] = int(line[4])
#
#             graph.add_node(start, station = line[0], time_stamp = line[1])
#             graph.add_node(end, station = line[2], time_stamp = line[3])
#
#             # we assume a unique edge between events for now
#             if not graph.has_edge(start, end):
#                 graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))

# def add_sources_and_sinks(graph, inspectors, flow_var_names, var_passengers_inspected):
    # for k, vals in inspectors.items():
    #     source = "source_" + str(k)
    #     sink = "sink_"+str(k)
    #     graph.add_node(source, station = vals['base'], time_stamp = None)
    #     graph.add_node(sink, station = vals['base'], time_stamp = None)
    #     for node in graph.nodes():
    #         if (graph.nodes[node]['station'] == vals['base']) and (graph.nodes[node]['time_stamp'] is not None):
    #
    #             # adding edge between sink and events and adding to the variable dictionary
    #             graph.add_edge(source, node, num_passengers = 0, travel_time = 0)
    #             flow_var_names.append('var_x_{}_{}_{}'.format(source, node, k))
    #             var_passengers_inspected['var_M_{}_{}'.format(source, node)] = 0
    #             graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
    #             flow_var_names.append('var_x_{}_{}_{}'.format(node, sink, k))
    #             var_passengers_inspected['var_M_{}_{}'.format(node, sink)] = 0


def start_cplex(c, flow_var_names, var_passengers_inspected):
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

def enumerate_all_shortest_paths(graph, OD):
    shortest_paths, arc_paths = create_arc_paths(graph)
    all_paths = {}
    for source, value in shortest_paths.items():
        for sink, path in value.items():
            # exclude paths from nodes to themselves
            if source != sink and (OD[(source, sink)] > 0.001):
                all_paths[(source, sink)] = path
    path_idx = {path:i for i,path in enumerate(all_paths)}
    return all_paths, path_idx

# def initialize_cplex(c, OD, flow_var_names, var_portion_of_passengers_inspected):

    # c.set_problem_type(c.problem_type.LP)
    # c.objective.set_sense(c.objective.sense.maximize)	# formulated as a maximization problem
    #
    #
    # #========================= ADDING VARIABLES AND OBJECTIVE FUNCTION ==============================
    #
    # print("Adding variables...", end=" ")
    #
    # # adding objective function and declaring variable types
    # c.variables.add(
    #     names = flow_var_names,
    #     types = [ c.variables.type.binary ] * len(flow_var_names)
    # )
    #
    # # defining the objective function coefficients
    # obj = [OD[(source, sink)] for source, sink in OD.keys()]
    # c.variables.add(
    #     names = var_portion_of_passengers_inspected,
    #     lb = [0] * len(var_portion_of_passengers_inspected),
    #     ub = [1] * len(var_portion_of_passengers_inspected),
    #     obj = obj,
    #     types = [ c.variables.type.continuous ] * len(var_passengers_inspected)
    # )

# def constr_mass_balance(c, graph, inspectors):
    # for k in inspectors:
    #     for node in graph.nodes():
    #         if graph.nodes[node]['time_stamp']:
    #
    #             in_indices = []
    #
    #             for p in graph.predecessors(node):
    #                 if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k): # not a sink/source
    #                     in_indices.append('var_x_{}_{}_{}'.format(p, node, k))
    #             in_vals = [1] * len(in_indices)
    #
    #             out_indices = []
    #
    #             for p in graph.successors(node):
    #                 if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k):
    #                     out_indices.append('var_x_{}_{}_{}'.format(node, p, k))
    #
    #             out_vals = [-1] * len(out_indices)
    #
    #             c.linear_constraints.add(
    #                 lin_expr = [cplex.SparsePair(
    #                                 ind = in_indices + out_indices,
    #                                 val = in_vals + out_vals
    #                             )],
    #                 senses = ['E'],
    #                 rhs = [0],
    #                 names = ['mass_balance_constr_{}_{}'.format(node, k)]
    #             )


# def constr_sink_source(c, graph, inspectors):
    # for k, vals in inspectors.items():
    #     sink = "sink_" + str(k)
    #     source = "source_" + str(k)
    #
    #     c.linear_constraints.add(
    #         lin_expr = [cplex.SparsePair(
    #                         ind = ['var_x_{}_{}_{}'.format(u, sink, k) for u in graph.predecessors(sink)],
    #                         val = [1] * graph.in_degree(sink)
    #                     )],
    #         senses = ['E'],
    #         rhs = [1],
    #         names = ['sink_constr_{}'.format(k)]
    #     )
    #
    #     c.linear_constraints.add(
    #         lin_expr = [ cplex.SparsePair(
    #                         ind = ['var_x_{}_{}_{}'.format(source, u, k) for u in graph.successors(source)] ,
    #                         val = [1] * graph.out_degree(source)
    #                     )],
    #         senses = ['E'],
    #         rhs = [1],
    #         names = ['source_constr_{}'.format(k)]
    #     )

# def constr_working_hours(c, graph, inspectors):
    # for k, vals in inspectors.items():
    #     source = "source_" + str(k) + ""
    #     sink = "sink_" + str(k)
    #     c.linear_constraints.add(
    #         lin_expr = [cplex.SparsePair(
    #                     ind = ['var_x_{}_{}_{}'.format(u, sink, k) for u in graph.predecessors(sink)]
    #                         + ['var_x_{}_{}_{}'.format(source, v, k) for v in graph.successors(source)],
    #                     val = [time.mktime(parse(graph.nodes[u]['time_stamp']).timetuple())
    #                                     for u in graph.predecessors(sink)]
    #                         + [-time.mktime(parse(graph.nodes[v]['time_stamp']).timetuple())
    #                                     for v in graph.successors(source)]
    #                         )],
    #         senses = ['L'],
    #         rhs = [vals['working_hours'] * HOUR_TO_SECONDS],
    #         names = ['time_flow_constr_{}'.format(k)]
    #     )


# def constraint_9(c, graph, inspectors):
#     for u, v in graph.edges():
#         if not ("source_" in u+v or "sink_" in u+v):
#             indices = ['var_M_{}_{}'.format(u,v)] + ['var_x_{}_{}_{}'.format(u,v,k) for k in inspectors]
#             values = [1] + [-vals["rate"] * graph.edges[u,v]['travel_time'] for k, vals in inspectors.items()]
#             c.linear_constraints.add(
#                 lin_expr = [cplex.SparsePair(ind = indices, val = values)], # needs to be checked
#                 senses = ['L'],
#                 rhs = [0],
#                 range_values = [0],
#                 names = ['bdd_by_inspector_count_{}_{}'.format(u, v)]
#             )
