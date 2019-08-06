import re
import pandas as pd

lines = []

with open('../Nate/Gurobi_Solution.sol', "r") as f:
    for line in f.readlines()[2:]:
        line = line.replace("\n","").split(" ")
        if 'var_x' in line[0] and abs(1-float(line[1])) < 0.1:
            lines.append(line)
            #print(line)
            
paths = [] 
#print(len(lines))

for l in lines:
    a = re.split("_|@|#", l[0])
    paths.append([a[2], a[3], a[4], a[5], a[6]])
    
    
#print(paths)

df = pd.DataFrame(paths, columns=['from', 'departure', 'to', 'arrival', 'inspector_id'])  
df.astype({'inspector_id':'int64'})

for i in range(3):
    path = df[df['inspector_id']==str(i)].sort_values(by=['departure'])
    print(path.to_string())
    
    






#df.groupby(['inspector_id']).apply(lambda x: x.sort_values(by=["departure"]))

#print(df)

#df.to_csv('sol.csv', index=False)

##print(df)

#print(df.dtypes)


    
