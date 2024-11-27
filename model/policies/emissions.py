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

def add_investment_tax_credit():
	"""
	Add an investment tax credit to a MESSAGEix scenario.
	This function modifies the provided MESSAGEix scenario to include an investment tax credit. 
	The specific implementation details, such as the tax credit rates and the affected technologies or sectors, 
	should be added within this function.
	Args:
		scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the investment tax credit will be added.
	Returns:
		None
	"""
	pass

def carbon_price():
	pass

def coal_phase_out(scenario, province, nodes_tax):
	"""
	Perform a coal phase-out operation on a MESSAGEix scenario.
	This function identifies all technologies related to coal, filters out certain technologies based on specific conditions,
	and then sets the upper bound of activity for these technologies to 0 in the specified years, effectively phasing out these
	coal technologies in the scenario.
	Args:
		scenario (MESSAGEix.Scenario): The scenario to perform the coal phase-out operation on.
		province (str): The province for which the coal phase-out is being implemented.
	Returns:
		None
	"""
	# Get all technologies
	technologies = scenario.set('technology')
	# Filter technologies containing 'coal'
	coal_technologies = technologies[technologies.str.contains('coal')]
	# Further filter technologies
	filtered_coal_technologies = coal_technologies[
		~coal_technologies.str.contains(r'(air|saline|fresh)$', regex=True, na=False)
	]
	# Filter out technologies starting with 'h2'
	coal_phaseout_tecs = filtered_coal_technologies[
		~filtered_coal_technologies.str.contains(r'^h2', regex=True)
	]
	# Get the years for the phase-out
	coal_phase_yrs = scenario.set('year')[16:]
	# Create a DataFrame for the upper bound of activity
	df = message_ix.make_df('bound_activity_up',
				 technology=coal_phaseout_tecs,
				 mode='M1',
				 value=0).pipe(
		broadcast,
		node_loc=nodes_tax,
		time='year',
		year_act=coal_phase_yrs,
		unit='-'
	).pipe(same_node)
	df['time'] = 'year'
	# Filter out certain rows
	condition = (df['node_loc'] == 'BritishColumbia') & (df['technology'] == 'coal_exp') & (df['year_act'] == 2030)
	filtered_df = df[~condition]
	# Update the scenario
    scenario.check_out()
	existing_df = scenario.par('bound_activity_up')
	scenario.remove_par('bound_activity_up', existing_df)
	scenario.add_par('bound_activity_up', filtered_df)
	scenario.commit('Coal phase-out implemented.')