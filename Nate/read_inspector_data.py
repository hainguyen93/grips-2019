import numpy as np

def inspectors(filename):
    Inspectors = {}
    with open(filename,'r') as f:
        f.readline()
        numInspectors=0
        for line in f.readlines():
            info = line.split(",")
<<<<<<< HEAD
            base = info[0].split(" ")[0]
            Inspectors[base] = []
            for j in range(int(info[1])):
                Inspectors[base].append((numInspectors,np.random.randint(4,9)))
                numInspectors+=1
            Inspectors[base].sort(key=lambda x: x[1])

    return Inspectors, numInspectors
=======
            #for j in range(int(info[1])):
            Inspectors[i] = {"base": info[0].split(" ")[0], "working_hours": np.random.randint(5,9), "rate": 10}
            i += 1

    return Inspectors
>>>>>>> 7d099262e559140637fab8875b6c06ad9d4622cd
