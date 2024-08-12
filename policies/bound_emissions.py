"""
This module provides a function to bound emissions in an extreme climate mitigation scenario.
"""

import pandas as pd
import numpy as np
import pycountry
from geotext import GeoText
from itertools import product

def expand_grid(dictionary):
    """
    Create a DataFrame from all combinations of dictionary values.

    Args:
        dictionary (dict): A dictionary where each key is a column name and the value is a list of column values.

    Returns:
        pd.DataFrame: A DataFrame containing all combinations of the provided values.
    """
    return pd.DataFrame([row for row in product(*dictionary.values())], columns=dictionary.keys())

def bound_emissions(msgSDG, nodeName):
    """
    Bound emissions in an extreme climate mitigation scenario.

    This function creates and commits a parameter 'bound_emission' for a given node in the MESSAGEix model.

    Args:
        msgSDG (message_ix.Scenario): The MESSAGEix scenario object.
        nodeName (str): The name of the node to bound emissions for.

    """
    msgSDG.check_out()

    # Define the years for bounding emissions
    year_df = [2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2070]

    # Define the dictionary for emissions bounding
    dic = {
        'node': [nodeName],
        'type_emission': ['TCE'],
        'type_tec': ['all'],
        'type_year': year_df,
        'value': [100, 90, 72.79, 50, 45, 40, 35, 30, 30],
        'unit': ['MtCO2']
    }

    # Create the DataFrame using expand_grid
    df = expand_grid(dic)
    df = df.iloc[0:9]  # Select the first 9 rows
    df['type_year'] = year_df

    # Add the parameter to the scenario and commit the changes
    msgSDG.add_par('bound_emission', df)
    msgSDG.commit('emissions bounded')

