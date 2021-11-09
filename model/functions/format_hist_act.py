import pandas as pd

def format_hist_act(DATA):
    """This file format historical activity data
    DATA: path to message-ix data folder
    """
    
    historical_activity = pd.read_excel(DATA / 'canadian_historical_activity.xlsx')

    historical_activity.drop(columns = ['Model', 'Scenario'], inplace = True)

    historical_activity.rename(columns = {'Region': 'node',                            
                                      'Variable': 'technology',
                                      'Unit': 'unit'}, inplace = True)

    historical_activity = historical_activity.melt(id_vars = ['node', 'technology', 'unit'],
                                               var_name = 'year', 
                                               value_name = 'value')

    historical_activity = historical_activity.set_index(['node', 'technology', 'year', 'unit']).sort_index().reset_index()
    
    return historical_activity
    