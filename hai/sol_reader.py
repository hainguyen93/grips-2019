import re
import pandas as pd
import sys

def main(argv):
    if len(argv) != 1:
        print('Enter input file only')
        sys.exit()
        
    lines = []

    with open(argv[0], "r") as f:
        for line in f.readlines()[2:]:
            line = line.replace("\n","").split(" ")
            if 'var_x' in line[0] and abs(1-float(line[1])) < 0.1:
                lines.append(line)
                        
    paths = [] 
    #print(len(lines))

    for l in lines:
        a = re.split("_|@|#", l[0])
        paths.append([a[2], a[3], a[4], a[5], a[6]])
    
    
    #print(paths)

    df = pd.DataFrame(paths, columns=['from', 'departure', 'to', 'arrival', 'inspector_id'])  
    df.astype({'inspector_id':'int64'})

    for i in range(6):
        path = df[df['inspector_id']==str(i)].sort_values(by=['departure'])
        print(path.to_string())
    
    

if __name__=='__main__':
    main(sys.argv[1:])



    
