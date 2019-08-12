# codes for extracting inspectors information from the inpectors input file
# @authors: Hai Nguyen, Ruby Abrams and Nathan May

import numpy as np


def extract_inspectors_data(file_name):
    """Extract a dictionary containing information for inspectors
    from the input file for inspectors

    Attribute:
        file_name : name of inspectors input file
    """
    print('Loading inspectors...', end=' ')
    data = pd.read_csv(file_name)
    inspectors={ data.loc[i]['Inspector_ID']:
                    {"base": data.loc[i]['Depot'], 
                     "working_hours": data.loc[i]['Max_Hours']}
                    for i in range(len(data))}
    print('There are {} inspectors in total'.format(len(inspectors)))
    return inspectors



def create_depot_inspector_dict(inspector_dict):
    """Create a new dict with keys being depot and value being a list of
    inspector_id, sorted in descending order according
    to the max_working_hours

    Attributes:
        inspector_dict : dict of inspectors
    """
    res = dict()    
    for inspector, val in inspector_dict.items():
        if not val['base'] in res:
            res[val['base']] = [(inspector, val['working_hours'])]
        else:
            res[val['base']].append((inspector, val['working_hours']))
    for val in res.values():
        val.sort(key=lambda x: x[1], reverse=True)    
    res = {k:[i[0] for i in val] for k, val in res.items()}
    return res

