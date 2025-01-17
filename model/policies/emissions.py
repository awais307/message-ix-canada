import numpy as np
import pandas as pd
import os
import sys
import message_ix
import ixmp

from pathlib import Path
from typing import Union
from model.utils import expand_grid
from message_ix_models.util import (
	broadcast,
	make_matched_dfs,
	same_node,
	same_time,
)



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

def add_federal_carbon_tax():
	"""
	Add a federal carbon tax to a MESSAGEix scenario.
	This function will modify the provided MESSAGEix scenario to include a federal carbon tax. 
	The specific implementation details, such as the tax rates and the affected sectors, 
	should be added within this function.
	Args:
		scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the federal carbon tax will be added.
	Returns:
		None
	"""
	pass

def add_provincial_carbon_tax(scenario, province):
	"""
	Add a provincial carbon tax to a MESSAGEix scenario.
	This function modifies the provided MESSAGEix scenario to include a provincial carbon tax 
	for a specified province. The specific implementation details, such as the tax rates, 
	affected sectors, and the time period for the tax, should be added within this function.
	Args:
		scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the provincial carbon tax will be added.
		province (str): The name of the province for which the carbon tax is being implemented.
	Returns:
		None
	"""
	pass



def carbon_price():
	pass
