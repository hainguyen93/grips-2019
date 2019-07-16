# Implementation of Multiproportional algorithm
# for OD matrix estimation
# author: Ruby Abrams

import numpy as np

def does_converge(V, V_hat, epsilon = 0.05):
    '''
    check to see if passes the convergence criterion:
    relative error needs to be less than 5%
    '''
    relative_error = np.abs(V_hat - V)/V_hat
    if (relative_error < epsilon).all():
        return True
    return False

def multiproportional(arc_paths):
    '''
    will read through the dictionary of the following structure
    arc_paths = {arc: [weight, ['node1','node2',...,'noden'],...,['node1',...,'nodem']]}
    and output a vector X which will be used to determine
    entries of OD matrix
    '''
    # will create a dictionary refering to the index of each arc
    arc_idx = {arc: i for i,arc in enumerate(arc_paths)}

    # local variables
    n = 0 # iteration number
    L = len(arc_paths) # total number of links/arc_idx
    X = np.ones(L)
    V = np.ones(L) # storage for converging weights
    V_hat = np.ones(L) # true weights

    # collect all true weights for every arc
    for arc, value in arc_paths.items():
        V_hat[arc_idx[arc]] = value[0]

    while not does_converge(V, V_hat):
        # for each arc a
        for arc, value in arc_paths.items():
            total = 0 # used to collect sums of products of X_a's
            num_paths = len(value) - 1
            # sum over all products of X_a's for each path running through this arc
            for path_index in xrange(num_paths):
                path = value[path_index+1] # this is one path through the arc
                # iterate through each pair of nodes in the path
                # and collect X_a values
                X_temp = np.array([ X[arc_idx[node1+'-->'+node2]] for node1,node2 in zip(path, path[1:]) ])
                # for each path, compute the product of X_a's
                # and add it to the running total for each arc
                total += np.product(X_temp)

            # intermediary step
            Y_a = V_hat[arc_idx[arc]]/total
            # update the arc X_a value
            X[arc_idx[arc]] = X[arc_idx[arc]]*Y_a
            # update converging values of V_a
            V[arc_idx[arc]] = total
        # update iteration number n
        n+=1
    return X
