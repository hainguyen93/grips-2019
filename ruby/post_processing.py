# post-processing the output
# to get the timetable for each inspectors

# read the var_x file first
with open("../ruby_code/res1/var_x.txt", "r") as x_file:
    xs = x_file.read()
    #xs = [i for i in xs if i]
    
# read the x values file
with open("../ruby_code/res1/res1.txt", "r") as x_val_file:
    x_vals = x_val_file.read().replace("\n","")
    #x_vals = [float(x) for x in x_vals]
    
# print out some output
print(len(xs))
print(len(x_vals))

#print(len(xs))
#print(len(x_vals))
