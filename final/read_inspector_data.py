import numpy as np

def inspectors(filename):
    Inspectors = {}
    with open(filename,'r') as f:
        f.readline()
        i = 0
        for line in f.readlines():
            info = line.split(",")
            #for j in range(int(info[1])):
            Inspectors[i] = {"base": info[0].split(" ")[0], "working_hours": np.random.randint(5,9), "rate": 10}
            i += 1

    return Inspectors
