import networkx as nx
from convergence_algorithm import *

def odEstimation(G):

    #remove waiting edges from our graph
    waiting_edges = [];
    for u,v in G.edges():
        if G[u][v]['num_passengers'] == 0:
            waiting_edges.append((u,v))
    G.remove_edges_from(waiting_edges)

    arc_paths = {}

    for (u,v,c) in G.edges.data('num_passengers'):
        arc_paths[u + '-->' + v] = [c]

    paths = dict(nx.all_pairs_shortest_path(G))
    print(paths.__sizeof__())

    ##compute proportions by finding shortest paths
    for source in paths:
        for sink in paths[source]:
            for u,v in zip(paths[source][sink],paths[source][sink][1:]):
                arc_paths[u + '-->' + v].append(paths[source][sink])
    return arc_paths


# def main():
#     # create set of all paths traveling through each arc
#     arc_paths = odEstimation(graph)
#     # implement the multiproportional algorithm
#     X = multiproportional(arc_paths)
#     # generate the OD-matrix disctionary (sparse representation)
#     T = generate_OD_matrix(arc_paths, X)
#
#     print(T)
#     quit()

if __name__ == '__main__':
    odEstimation()
