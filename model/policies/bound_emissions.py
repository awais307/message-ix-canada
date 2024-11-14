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

def bound_emissions(self,path, nodeName):
    """
    Bound emissions in an extreme climate mitigation scenario.

    This function creates and commits a parameter 'bound_emission' for a given node in the MESSAGEix model.

    Args:
        msgSDG (message_ix.Scenario): The MESSAGEix scenario object.
        nodeName (str): The name of the node to bound emissions for.

    """
    self.scenario.check_out()

    emissions_df = pd.read_csv(path/'emissions_baseline.csv')
    

    # Define the exact emissions trajectory for Canada (in MtCO2eq)
    canada_trajectory = {
        2020: 659e6,   # 659 MtCO2eq
        2025: 549e6,   # 549 MtCO2eq
        2030: 439e6,   # 439 MtCO2eq
        2035: 329e6,   # 329 MtCO2eq
        2040: 220e6,   # 220 MtCO2eq
        2045: 110e6,   # 110 MtCO2eq
        2050: 50e6,    # 50,000 MtCO2eq (likely meant to be 50 MtCO2eq)
        2055: 40e6,    # 40,000 MtCO2eq (likely meant to be 40 MtCO2eq)
        2060: 30e6     # 30,000 MtCO2eq (likely meant to be 30 MtCO2eq)
    }

    # Extract the unique provinces (nodes) excluding Canada
    provinces = emissions_df['node'].unique()
    provinces = provinces[provinces != 'Canada']

    # Initialize a list to store the emission trajectories for each province
    emission_trajectories_list = []

    # Iterate over each province and apply the reduction schedule
    for province in provinces:
        # Extract the emission data for the province
        province_data = emissions_df[(emissions_df['node'] == province)]
        
        # Create a dictionary to store the year and emission values
        province_emissions = {'province': [], 'year': [], 'emission': []}
        
        # Get the 2020 base year emission for the province
        base_year_emission = province_data[province_data['year'] == 2020]['lvl'].values[0]
        
        # Get the total emissions for Canada in 2020
        canada_2020_emission = canada_trajectory[2020]
        
        # Calculate the proportion of this province's emissions relative to Canada's total in 2020
        province_proportion = base_year_emission / canada_2020_emission
        
        # Iterate over the Canada trajectory and calculate the emissions for this province
        for year, canada_target in canada_trajectory.items():
            adjusted_emission = province_proportion * canada_target
            
            # Store the emission value in the dictionary
            province_emissions['province'].append(province)
            province_emissions['year'].append(year)
            province_emissions['emission'].append(adjusted_emission)
        
        # Convert the dictionary to a DataFrame and append to the list
        province_emissions_df = pd.DataFrame(province_emissions)
        emission_trajectories_list.append(province_emissions_df)

    # Concatenate all the DataFrames into a single DataFrame
    emission_trajectories_df = pd.concat(emission_trajectories_list).reset_index(drop=True)

    df_bound = emission_trajectories_df.copy()
    df_bound.rename(columns={'province':'node','year':'type_year','emission':'value'}, inplace=True)
    df_bound['type_emission'] = 'TCE'
    df_bound['type_tec'] = 'all'
    df_bound['unit'] = '-'

    self.scenario.add_par('bound_emission', df_bound)


    self.scenario.add_par('bound_emission', df)
    self.scenario.commit('emissions bounded')

