import sys
import os
import xml.etree.ElementTree as ET
import json

from exceptions import *
from my_xml_parser import *
from Main_Gurobi import *

# suppose we read in a true solution.
# i.e. newsolution are values to known variables



# add heuristic solutions
def heuristic_solution(model, where):
    if where == GRB.Callback.MIPNODE:
        model.cbSolution(vars, newsolution)
