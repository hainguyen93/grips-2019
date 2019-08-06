# Input: Data file in Forward Star format
# Output: Digraph object
# Function: This file will be used to read in information to
# create the DiGraph object and write it to another file
# @author: Ruby Abrams, Hai Nguyen, Nate May

from __future__ import division

import sys

# change local PATH environment for Python
sys.path.append('/nfs/optimi/usr/sw/cplex/python/3.6/x86-64_linux')

import cplex
from gurobipy import *
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
import pandas as pd
from copy import deepcopy

from OD_matrix import *
from read_inspector_data import *

# networkx start
graph = nx.DiGraph() # nx.MultiDiGraph()

<<<<<<< HEAD:final/ReformulatedLP.py
inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 12},
              1 : {"base": 'HH', "working_hours": 5, "rate": 10},
              2 : {"base": 'AHAR', "working_hours": 6, "rate": 15}
              #3 : {"base": 'FGE', "working_hours": 8, "rate": 10},
              #4 : {"base": 'HSOR', "working_hours": 7, "rate": 10},
              #5 : {"base": 'RM', 'working_hours': 5, 'rate':11}
              }

=======
#inspectors = { 0 : {"base": 'RDRM', "working_hours": 8, "rate": 10},
              #1 : {"base": 'HH', "working_hours": 8, "rate": 10},
              #2 : {"base": 'AHAR', "working_hours": 8, "rate": 10},
              #3 : {"base": 'FGE', "working_hours": 8, "rate": 10},
              #4 : {"base": 'HSOR', "working_hours": 8, "rate": 10},
              #5 : {"base": 'RM', 'working_hours': 8, 'rate':10}
              #}
maxInspectors = 10;


inspectors = inspectors("GRIPS2019_401.csv")

# Assumption: rate of inspection remains constant
>>>>>>> Nate:Nate/Main_Gurobi.py
KAPPA = 12
flow_var_names = []

# new reformulation variable
var_m = np.array([])

HOUR_TO_SECONDS = 3600
MINUTE_TO_SECONDS = 60

#============================= CONSTRUCTING THE GRAPH ============================================

print("Building graph ...", end = " ")
t1 = time.time()

input_dir = 'new_arcs.txt'

with open(input_dir, "r") as f:
    for line in f.readlines()[:-1]:
        line = line.replace('\n','').split(' ')
        start = line[0]+'@'+line[1]
        end = line[2]+'@'+line[3]

        for k in inspectors:
            flow_var_names.append((start, end, k))

        graph.add_node(start, station = line[0], time_stamp = line[1])
        graph.add_node(end, station = line[2], time_stamp = line[3])

        # we assume a unique edge between events for now
        if not graph.has_edge(start, end):
            graph.add_edge(start, end, num_passengers= int(line[4]), travel_time =int(line[5]))


# time to build graph
t2 = time.time()

print('Finished! Took {:.5f} seconds'.format(t2-t1))

#================================ OD Estimation ===============================
print("Estimating OD Matrix ...", end = " ")

# create a deep copy of the graph
new_graph = deepcopy(graph)

nodes = graph.nodes()

shortest_paths, arc_paths = create_arc_paths(new_graph)

T, OD = generate_OD_matrix(nodes, shortest_paths, arc_paths)

numPassengers = sum(list(OD.values()))

# Create a dictionary of all Origin-Destinations
all_paths = {}
for source, sink in OD.keys():
    if source != sink:
        all_paths[(source, sink)] = shortest_paths[source][sink]

path_idx = {path:i for i,path in enumerate(all_paths)}


t2a = time.time()
print('Finished! Took {:.5f} seconds'.format(t2a-t2))

#============================== ADDING SOURCE/SINK NODES ==========================================

print("Adding Sinks/Sources...", end=" ")

for k, vals in inspectors.items():
    source = "source_" + str(k)
    sink = "sink_"+str(k)
    graph.add_node(source, station = vals['base'], time_stamp = None)
    graph.add_node(sink, station = vals['base'], time_stamp = None)
    for node in graph.nodes():
        if (graph.nodes[node]['station'] == vals['base']) and (graph.nodes[node]['time_stamp'] is not None):
            # adding edge between sink and events and adding to the variable dictionary
            graph.add_edge(source, node, num_passengers = 0, travel_time = 0)
            flow_var_names.append((source, node, k))
            graph.add_edge(node, sink, num_passengers=0, travel_time = 0 )
            flow_var_names.append((node, sink, k))


t3 = time.time()

print('Finished! Took {:.5f} seconds'.format(t3-t2a))

# test edge source to sinks
# print('TEST: Unique edge between two nodes: ', num_edges == graph.number_of_edges())
print("TEST: No Source-Sink Edge: ", not graph.has_edge("source_0", "sink_0"))

# freeze graph to prevent further changes
graph = nx.freeze(graph)

#================================== START Gurobi ================================================
#                           Establish Maximization Problem
#================================================================================================

print("Start Gurobi")

model = Model("DB_MIP");

#========================= ADDING VARIABLES AND OBJECTIVE FUNCTION ==============================

print("Adding variables...", end=" ")

x = model.addVars(flow_var_names,ub =1,lb =0,obj = 0,vtype = GRB.BINARY,name = 'x')
M = model.addVars(OD.keys(), lb = 0,ub = 1, obj = list(OD.values()), vtype = GRB.CONTINUOUS,name = 'M');


# Adding the objective function coefficients
model.setObjective(M.prod(OD),GRB.MAXIMIZE)
#model.addConstr(M.prod(OD),GRB.LESS_EQUAL,numPassengers*(0.8),"objective upper-bound") #TEST!

t4 = time.time()
print("Finished! Took {:.5f} seconds".format(t4-t3))

#=================================== CONSTRAINT 6 ===================================================
#                              Mass - Balance Constraint
#================================================================================================
print("Adding Constraint (6) [Mass - Balance Constraint] ...", end=" ")

for k in inspectors:
    for node in graph.nodes():
        if graph.nodes[node]['time_stamp']:

            in_x = [] #list of in_arc variables

            for p in graph.predecessors(node):
                if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k): # not a sink/source
                    in_x.append(x[p, node, k])

            in_vals = [1] * len(in_x)
            in_exp = LinExpr(in_vals,in_x)

            out_x = []#list of out-arc variables

            for p in graph.successors(node):
                if graph.nodes[p]['time_stamp'] or p.split('_')[1] == str(k):
                    out_x.append(x[node, p, k])

            out_vals = [-1] * len(out_x)
            out_exp = LinExpr(out_vals,out_x)

            in_exp.add(out_exp) #combine in-arc & out-arc linear expressions
            model.addConstr(in_exp,GRB.EQUAL,0,"mass_bal_{}_{}".format(node,str(k))) #add constraint to model



t5 = time.time()

print('Finished! Took {:.5f} seconds'.format(t5-t4))


#=================================== CONSTRAINT 7 ===============================================
#                              Sink and Source Constraint
#================================================================================================

print("Adding constraint (7) [Sink and Source Constraint]...", end=" ")


for k, vals in inspectors.items():
    sink = "sink_" + str(k)
    source = "source_" + str(k)

    sink_constr = LinExpr([-1] * graph.in_degree(sink),[x[u, sink, k] for u in graph.predecessors(sink)])
    #model.addConstr(sink_constr, GRB.EQUAL, 1,"sink_constr_{}".format(k))

    source_constr = LinExpr([1] * graph.out_degree(source),[x[source, u, k] for u in graph.successors(source)])
    sink_constr.add(source_constr) #combine

    model.addConstr(sink_constr, GRB.EQUAL, 0,"source_constr_{}".format(k))
    model.addConstr(source_constr, GRB.LESS_EQUAL, 1,"source_constr_{}".format(k))

    if k == 0:
        maxWorking = source_constr
    else:
        maxWorking.add(source_constr)

model.addConstr(maxWorking,GRB.LESS_EQUAL,maxInspectors,"Max_Inspector_Constraint")

t6 = time.time()
print('Finished! Took {:.5f} seconds'.format(t6-t5))


#===================================== CONSTRAINT 8 ==================================================
#                        Time Flow/Number of Working Hours Constraint
#================================================================================================

print("Adding Constraint (8) [Time Flow Constraint]...", end=" ")

for k, vals in inspectors.items():
    source = "source_" + str(k) + ""
    sink = "sink_" + str(k)

    ind = [x[u, sink, k] for u in graph.predecessors(sink)] + [x[source, v, k] for v in graph.successors(source)]
    val = [time.mktime(parse(graph.nodes[u]['time_stamp']).timetuple()) for u in graph.predecessors(sink)] + [-time.mktime(parse(graph.nodes[v]['time_stamp']).timetuple()) for v in graph.successors(source)]

    time_flow = LinExpr(val,ind)
    model.addConstr(time_flow,GRB.LESS_EQUAL,vals['working_hours'] * HOUR_TO_SECONDS,'time_flow_constr_{}'.format(k))


t7 = time.time()
print("Finished! Took {:.5f} seconds".format(t7-t6))


#================================== CONSTRAINT 9 ==========================================
#                   Minimum Constraint (Linearizing the Objective Function)
#================================================================================================

print('Adding Constraint (9) [Minimum Constraint]...', end = " ")

for (u, v), path in all_paths.items():
    if not ("source_" in u+v or "sink_" in u+v):

        indices = [M[u,v]] + [x[i,j,k] for i,j in zip(path, path[1:]) for k in inspectors]
        values = [1] + [-KAPPA * graph.edges[i,j]['travel_time']/graph.edges[i,j]['num_passengers'] for i,j in zip(path, path[1:]) for k in inspectors]

        min_constr = LinExpr(values,indices)
        model.addConstr(min_constr,GRB.LESS_EQUAL,0,"minimum_constr_path_({},{})".format(u,v))

t8 = time.time()
print("Finished! Took {:.5f} seconds".format(t8-t7))


#================================== POST-PROCESSING ================================================


#Set Parameters:

<<<<<<< HEAD
<<<<<<< HEAD
model.setParam("MIPGap",.05)
#model.setParam("MIPFocus",1)
=======
model.Param.MIPGap = 
>>>>>>> master
=======
model.Param.MIPGap = 
>>>>>>> master

model.optimize()
model.write("Gurobi_Solution.mps")
model.write("Gurobi_Solution.lp")
model.write("Gurobi_Solution.rlp")

#Write Solution:
#----------------------------------------------------------------------------------------------

with open("Gurobi_Solution.txt", "w") as f:
    for k in inspectors:
        start = "source_{}".format(k)
        while(start != "sink_{}".format(k)):
            arcs = x.select(start,'*',k)
            try:
                match = [x for x in arcs if x.getAttr("x") != 0]

                arc = match[0].getAttr("VarName").split(",")
                start = arc[1]
                arc[0] = arc[0].split("[")[1]
                arc = arc[:-1]
            except:
                break

            f.write(" ".join(arc)+"\n")
f.close()

def setSolution(x,inspectors,delta):
    prevSolution = [z for z in x if z.getAttr("x") == 1]
    zeros = []

    for base in inspectors.keys():
        for(u,v) in inspectors[base][:delta+1]:
            if prevSolution.select('*','*',u):
                inspectors[base].remove((u,v))
        for (u,v) in inspectors[base][delta:]:
            zeros.append(x.select('*','*',u))

    solution = prevSolution + zeros
    vals = [1]*len(prevSolution) + [0]* len(zeros)

    return solution, vals, inspectors