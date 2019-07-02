# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# Author: Ruby Abrams

import networkx as nx

# networkx start
graph = nx.DiGraph()

with open('../Data/digraph_data', "r") as file:
    for line in file.readlines()[:-1]:
        line = line.replace('\n','').split(' ')
        print(line)
        graph.add_edge(" ".join(line[:2]), " ".join(line[2:4]), num_passengers = int(line[4]), travel_time = int(line[5]))

nx.write_gexf(graph, "test.gexf")
