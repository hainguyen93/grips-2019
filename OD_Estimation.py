import networkx as nx
from plot_printgraph import PrintGraph

def od_Estimation(G):

    node_ref = {};#master index for all nodes
    arc_ref = {}; #master index for all arcs
    P = [[0]*G.number_of_nodes()]*G.number_of_nodes(); #proportion matrix - all or none

    #fill node_ref
    i=0
    for node in G.nodes():
        node_ref[node] = i;
        i +=1

    #fill rac_ref
    i = 0
    for (u,v,c) in G.edges.data('num_passengers'):
        arc_ref[u + '-->' + v] = [i, c];

        print(u + '-->' + v + ': '+str(i)+', '+str(c))

        i += 1

    #paths = dict(nx.all_pairs_shortest_path(G))

    #compute proportions by finding shortest paths
    #for source in paths:
        #for sink in paths[source]:
            #P[node_ref[source]][node_ref[sink]] = paths[source][sink]

    #print(P)