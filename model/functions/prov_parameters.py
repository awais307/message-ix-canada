import pandas as pd

"""This function creates a dictionary of provincial parameter dataframes by copying national ones"""

def generator(msg):
    
    provinces = ['Alberta',
             'BritishColumbia',
             'Manitoba',
             'NewBrunswick',
             'NewfoundlandandLabrador',
             'NorthwestTerritories',
             'NovaScotia',
             'Nunavut',
             'Ontario',
             'PrinceEdwardIsland',
             'Quebec',
             'Saskatchewan',
             'Yukon']
    
    # Create dictionary to store parameter : <columns containing 'node'> pairs
    pars_to_change = {}

    # Iterate through parameters
    for par in msg.par_list():
        # Create list for appending 'node' containing columns
        node_stuff = []

        # Iterate through columns of parameter dataframe
        for col in msg.par(par).columns:

            # Check for node column (or some variation including string 'node')
            if 'node' in col:
                # Add column to list
                node_stuff.append(col)

        if len(node_stuff) != 0:
            # Add parameter and column values to dictionary
            pars_to_change[par] = node_stuff

    # Remove parameters I've already found
    pars_to_change.pop('demand')
    pars_to_change.pop('historical_activity')
    
    # Create dictionary with key = <parameter name> and value = <list of provincial dataframes>
    dfs = dict.fromkeys(pars_to_change.keys())

    for par in dfs.keys():
        # Create empty list to store dataframes
        dfs[par] = []

        for prov in provinces:
            # Copy Canadian dataframe
            df = msg.par(par).copy()

            for node_data in pars_to_change[par]:
                # Change node value to province
                df[node_data] = prov

            # Append provincial dataframe to list for this parameter
            dfs[par].append(df)
    
    return dfs