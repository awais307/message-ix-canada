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
        if not msg.par(par).empty:
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
    
    # Create dictionary with key = <parameter name> and value = provincial dataframe
    dfs = dict.fromkeys(pars_to_change.keys())

    for par in dfs.keys():    
        # Create empty dataframe to store data
        dfs[par] = pd.DataFrame(columns = msg.par(par).columns)

        for prov in provinces:
            # Create copy of Canadian dataframe
            df = msg.par(par).copy()

            for node_data in pars_to_change[par]:
                # Change node value to province
                df[node_data] = prov

            # Append provincial data to parameter dataframe
            dfs[par] = dfs[par].append(df)
    
    return dfs