"""
This module provides functions to implement various energy policies in MESSAGEix scenarios, 
including hydrogen shares, federal carbon tax, and coal phase-out.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def add_hydrogen_shares(scenario, path):

    
    """
    Add hydrogen shares to a MESSAGEix scenario.

    This function modifies the provided MESSAGEix scenario to include hydrogen shares. 
    The specific implementation details, such as the hydrogen share percentages and the affected sectors, 
    should be added within this function.

    Args:
        scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the hydrogen shares will be added.

    Returns:
        None
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
