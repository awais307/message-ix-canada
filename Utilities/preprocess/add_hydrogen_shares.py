import pandas as pd
import numpy as np
from pathlib import Path

def add_hydrogen_shares(scenario, path):
    """
    Add hydrogen shares 
    TODO: Add more details about the function
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        path (str or Path): Path to the the historical activity data.
    """
    scenario.check_out() 
    
    data = pd.ExcelFile(path / 'hydrogen_shares.xlsx')
   
    # Loop through each sheet
    for sheet_name in data.sheet_names:
        # Perform operations on the DataFrame
        df = pd.read_excel(path /'hydrogen_shares.xlsx', sheet_name=sheet_name)
        print(f"Sheet name: {sheet_name}")
        if sheet_name in scenario.set_list():
            if sheet_name == 'cat_tec':
                continue
            scenario.add_set(sheet_name, df[sheet_name])
        elif sheet_name in scenario.par_list():
            scenario.add_par(sheet_name, df)
    
    scenario.commit('Updated historical activity based on new data')
