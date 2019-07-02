\ENCODING=ISO-8859-1
\Problem name: 

Minimize
 obj: 0 x + 0 w + 0 t + 7.2 var_x_0_1 - 2 var_w_0_1 + 0.5 var_t_0_1
      + 2 var_x_1_2 + 3 var_w_1_2 + 4 var_t_1_2 + var_w_1_6 + 0 var_t_1_6
Subject To
 constr_flow_conservation_0: - var_x_0_1  = 0
 constr_flow_conservation_1: var_x_0_1 - var_x_1_2 - var_x_1_6  = 0
 constr_flow_conservation_2: var_x_1_2  = 0
 constr_flow_conservation_6: var_x_1_6  = 0
 constr_flow_conservation_3:  = 0
Bounds
 0 <= x <= 1
      w >= 0
Binaries
 x 
Generals
 w 
End
