# Implementation of Multiproportional algorithm
# for OD matrix estimation
# author: Ruby Abrams, Hai Nguyen, Nate May

import numpy as np
import networkx as nx
from scipy.sparse import *
from scipy import *

# relative error
EPSILON = 0.02


def create_arc_paths(G):
    #remove edges without any passenger from our graph
    waiting_edges = [];
    for u,v in G.edges():
        if G.edges[u,v]['num_passengers'] == 0:
            waiting_edges.append((u,v))
    G.remove_edges_from(waiting_edges)

    arc_paths = {}

    for (u,v,c) in G.edges.data('num_passengers'):
        arc_paths[u + '-->' + v] = [c]

    paths = dict(nx.all_pairs_shortest_path(G))

    ##compute proportions by finding shortest paths
    for source in paths:
        for sink in paths[source]:
            if source == sink:
                continue
            for u,v in zip(paths[source][sink],paths[source][sink][1:]):
                # excluding paths from nodes to themselves
                #if source != sink:
                arc_paths[u + '-->' + v].append(paths[source][sink])
    return paths, arc_paths


def multiproportional(arc_paths):
    '''
    will read through the dictionary of the following structure
    arc_paths = {arc: [weight, ['node1','node2',...,'noden'],...,['node1',...,'nodem']]}
    and output a vector X which will be used to determine
    entries of OD matrix
    '''
    # will create a dictionary refering to the index of each arc
    arc_idx = {arc: i for i,arc in enumerate(arc_paths)}

    # local variables
    n = 0 # iteration number
    L = len(arc_paths) # total number of links/arc_idx
    X = np.ones(L)
    V = np.ones(L) # storage for converging weights
    V_hat = np.ones(L) # true weights

    # collect all true weights for every arc
    for arc, value in arc_paths.items():
        V_hat[arc_idx[arc]] = value[0]

    while not (np.abs(V_hat - V)/np.abs(V_hat) < EPSILON).all():
        # for each arc a
        for arc, value in arc_paths.items():
            total = 0 # used to collect sums of products of X_a's
            num_paths = len(value) - 1
            # sum over all products of X_a's for each path running through this arc
            for path_index in range(num_paths):
                path = value[path_index+1] # this is one path through the arc
                # iterate through each pair of nodes in the path
                # and collect X_a values
                X_temp = np.array([ X[arc_idx[node1+'-->'+node2]] for node1,node2 in zip(path, path[1:]) ])
                # for each path, compute the product of X_a's
                # and add it to the running total for each arc
                total += np.product(X_temp)

            # intermediary step
            Y_a = V_hat[arc_idx[arc]]/total
            # update the arc X_a value
            X[arc_idx[arc]] = X[arc_idx[arc]]*Y_a
            # update converging values of V_a
            V[arc_idx[arc]] = total
        # update iteration number n
        n+=1
    return X

def generate_OD_matrix(graph, shortest_paths, arc_paths):
    '''
    This will generate a sparse matrix of the OD generate_OD_matrix.
    Given the X vector and arc_paths, all non-zero entries will be returned in
    a dictionary whose key is the arc and value is the number of passengers of
    that kind.
    '''
    nodes = graph.nodes()
    N = len(nodes)
    nod_idx = {node: i for i,node in enumerate(nodes)}
    #shortest_paths, arc_paths = create_arc_paths(graph)
    X = multiproportional(arc_paths)
    T = dok_matrix((N,N))
    arc_idx = {arc: i for i,arc in enumerate(arc_paths)}

    # OD matrix dictionary
    OD = {}
    # iterate through all sources
    for source, val in shortest_paths.items():
        # for every sink
        for sink, path in val.items():
            # dont add include paths from a node to itself
            if sink != source:
                # collect the X_a values for all arcs in the path
                X_a = np.product(np.array([ X[ arc_idx[node1+'-->'+node2] ] for node1,node2 in zip(path, path[1:]) ]))
                T[ nod_idx[source] , nod_idx[sink] ] = X_a
                # populate a dictionary of the non-zero entries too
                OD[(source, sink)] = X_a
    return T, OD
