
from __future__ import division
import sys
import networkx as nx
import time

def construct_graph_from_file(input_dir, inspectors):
    """Construct graph from an external file

    Attributes:
        input_dir : name of the external file
        inspectors : dictionary of inspectors
    """
    print("Building graph ...", end=" ")
    t1 = time.time()

    graph = nx.DiGraph()  # nx.MultiDiGraph()
    flow_var_names = []

    with open(input_dir, "r") as f:
        for line in f.readlines()[:-1]:
            line = line.replace('\n', '').split(' ')
            start = line[0] + '@' + line[1]
            end = line[2] + '@' + line[3]

            for k in inspectors:
                flow_var_names.append((start, end, k))

            graph.add_node(start, station=line[0], time_stamp=line[1])
            graph.add_node(end, station=line[2], time_stamp=line[3])

            # we assume a unique edge between events for now
            if not graph.has_edge(start, end):
                graph.add_edge(start, end, num_passengers=int(
                    line[4]), travel_time=int(line[5]))

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2 - t1))

    return graph, flow_var_names



def construct_graph_from_edges(all_edges):
    """ Construct the graph from a list of edges

    Attribute:
        all_edges : list of 6-tuples (from, depart, to, arrival, num passengers, time)
    """
    print("Building graph ...", end=" ")
    t1 = time.time()

    graph = nx.DiGraph()  # nx.MultiDiGraph()
    flow_var_names = []

    for edge in all_edges:

        start = edge[0] + '@' + edge[1]
        end = edge[2] + '@' + edge[3]

        graph.add_node(start, station=edge[0], time_stamp=edge[1])
        graph.add_node(end, station=edge[2], time_stamp=edge[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers=int(
                edge[4]), travel_time=int(edge[5]))

    t2 = time.time()
    print('Finished! Took {:.5f} seconds'.format(t2 - t1))

    return graph  # , flow_var_names
