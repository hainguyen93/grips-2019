import networkx as nx

def odEstimation(G):

    #remove waiting edges from our graph
    waiting_edges = [];
    for u,v in G.edges():
        if G[u][v]['num_passengers'] == 0:
            waiting_edges.append((u,v))
    G.remove_edges_from(waiting_edges)


    arc_paths = {};




    for (u,v,c) in G.edges.data('num_passengers'):
        arc_paths[u + '-->' + v] = [c];

        #print(u + '-->' + v + ': '+str(i)+', '+str(c))


    paths = dict(nx.all_pairs_shortest_path(G))
    print(paths.__sizeof__())

    ##compute proportions by finding shortest paths
    for source in paths:
        for sink in paths[source]:
            for u,v in zip(paths[source][sink],paths[source][sink][1:]):

                arc_paths[u + '-->' + v].append(paths[source][sink])


    return arc_paths
