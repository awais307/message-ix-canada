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
def apply_obps_baseline(scenario, data_file_path: str):
	"""
	Apply the Output-Based Pricing System (OBPS) policy for the Baseline Canada Scenario
	to the given MESSAGEix scenario.
	This function modifies the scenario's fixed costs based on emissions intensity and carbon pricing.
	Args:
		scenario (ixmp.Scenario): The MESSAGEix scenario to apply the OBPS policy to.
		data_file_path (str): Path to the Excel file containing necessary data.
	"""
	# Read the required data
	# MA: Read the obps inputs clea excel file
	data_relation = pd.read_excel(data_file_path, sheet_name='relation_activity')
	# Define conditions for filtering the data
	conditions_2 = (
		data_relation['technology'].isin([
			'oil_extr_1', 'oil_extr_2', 'oil_extr_3', 'oil_extr_4', 'oil_extr_5', 'oil_extr_6',
			'cement_CO2', 'coal_extr', 'gas_extr_1', 'gas_extr_2', 'gas_extr_3', 'gas_extr_4', 
			'gas_extr_5', 'gas_extr_6'
		]) &
		(data_relation['relation'] == 'CO2_Emission') &
		(data_relation['node_rel'] == 'Alberta')
	)
	# Filter the data based on the conditions
	result = data_relation[conditions_2][['technology', 'value', 'node_rel', 'year_act']]
	# Initialize columns for calculations
	result['Emission Intensity Reduction_baseline'] = 0.0
	# Calculate Emission Intensity Reduction_baseline
	for index, row in result.iterrows():
		if 2020 < row['year_act'] < 2055:
			previous_year_value = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == row['year_act'] - 5), 
				'Emission Intensity Reduction_baseline'
			].values
			if len(previous_year_value) > 0:
				result.loc[index, 'Emission Intensity Reduction_baseline'] += previous_year_value[0] + 3.33/100
	# Calculate Emission intensity standard_Baseline Canada Scenario
	result['Emission intensity standard_Baseline Canada Scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] > 2020:
			value_cal = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2015), 
				'value'
			]
			if not value_cal.empty:
				result.at[index, 'Emission intensity standard_Baseline Canada Scenario'] = row['value'] - row['Emission Intensity Reduction_baseline'] * value_cal.values[0]
			else:
				value_cal = result.loc[
					(result['technology'] == row['technology']) & 
					(result['year_act'] == 2020), 
					'value'
				]
				result.at[index, 'Emission intensity standard_Baseline Canada Scenario'] = row['value'] - row['Emission Intensity Reduction_baseline'] * value_cal.values[0]
	# Calculate Payable emission intensity_Baseline scenario
	result['Payable emission intensity_Baseline scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] > 2020:
			result.loc[index, 'Payable emission intensity_Baseline scenario'] = row['value'] - row['Emission intensity standard_Baseline Canada Scenario']
	# Calculate carbon cost_Baseline Canada scenario
	rate = 0.73
	result['carbon cost_Baseline Canada scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] == 2025:
			result.loc[index, 'carbon cost_Baseline Canada scenario'] = row['Payable emission intensity_Baseline scenario'] * rate * 125
		elif row['year_act'] > 2025:
			result.loc[index, 'carbon cost_Baseline Canada scenario'] = row['Payable emission intensity_Baseline scenario'] * rate * 170
	# Adjust for years 2055 and 2060
	for index, row in result.iterrows():
		if row['year_act'] > 2050:
			value_to_assign = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2050), 
				'carbon cost_Baseline Canada scenario'
			].values
			if len(value_to_assign) > 0:
				result.at[index, 'carbon cost_Baseline Canada scenario'] = value_to_assign[0]
	# Merge with fix_cost data and update the scenario's fix_cost
	data_fixcost = pd.read_excel(data_file_path, sheet_name='fix_cost')
	merged_data = pd.merge(
		data_fixcost, 
		result[['technology', 'year_act', 'carbon cost_Baseline Canada scenario']],
		left_on=['technology', 'year_act'],
		right_on=['technology', 'year_act'],
		how='left'
	)
	merged_data['value'] = merged_data['value'] + merged_data['carbon cost_Baseline Canada scenario'].fillna(0)
	merged_data.drop(columns=['carbon cost_Baseline Canada scenario'], inplace=True)
	# Reintegrate the updated fix_cost data into the scenario
	for index, row in merged_data.iterrows():
		scenario.add_par('fix_cost', {
			'node_loc': 'Alberta',
			'technology': row['technology'],
			'year_vtg': row['year_act'],
			'year_act': row['year_act'],
			'mode': 'standard',
			'unit': 'USD/kWyr',
			'value': row['value']
		})

def apply_obps_netzero(scenario, data_file_path: str):
	"""
	Apply the Output-Based Pricing System (OBPS) policy for the Net Zero Scenario
	to the given MESSAGEix scenario.
	This function modifies the scenario's fixed costs based on emissions intensity and carbon pricing.
	Args:
		scenario (ixmp.Scenario): The MESSAGEix scenario to apply the OBPS policy to.
		data_file_path (str): Path to the Excel file containing necessary data.
	"""
	# Read the required data
	data_relation = pd.read_excel(data_file_path, sheet_name='relation_activity')
	# Define conditions for filtering the data
	conditions_2 = (
		data_relation['technology'].isin([
			'oil_extr_1', 'oil_extr_2', 'oil_extr_3', 'oil_extr_4', 'oil_extr_5', 'oil_extr_6',
			'cement_CO2', 'coal_extr', 'gas_extr_1', 'gas_extr_2', 'gas_extr_3', 'gas_extr_4', 
			'gas_extr_5', 'gas_extr_6'
		]) &
		(data_relation['relation'] == 'CO2_Emission') &
		(data_relation['node_rel'] == 'Alberta')
	)
	# Filter the data based on the conditions
	result = data_relation[conditions_2][['technology', 'value', 'node_rel', 'year_act']]
	# Initialize columns for calculations
	result['Emission Intensity Reduction_Net Zero Scenario'] = 0.0
	# Calculate Emission Intensity Reduction_Net Zero Scenario
	for index, row in result.iterrows():
		if 2055 > row['year_act'] > 2020:
			result.loc[index, 'Emission Intensity Reduction_Net Zero Scenario'] = (row['year_act'] - 2022) * 0.02
	# Calculate Emission intensity standard_Net zero
	result['Emission intensity standard_Net zero'] = 0.0
	for index, row in result.iterrows():
		if 2055 > row['year_act'] > 2020:
			result.loc[index, 'Emission intensity standard_Net zero'] = row['value'] * (1 - row['Emission Intensity Reduction_Net Zero Scenario'])
	# Calculate Payable emission intensity_Net zero
	result['Payable emission intensity_Net zero'] = 0.0
	for index, row in result.iterrows():
		if 2055 > row['year_act'] > 2020:
			result.loc[index, 'Payable emission intensity_Net zero'] = row['value'] - row['Emission intensity standard_Net zero']
	# Calculate carbon cost_Net zero scenario
	rate = 0.73
	result['carbon cost_Net zero scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] == 2025:
			result.loc[index, 'carbon cost_Net zero scenario'] = row['Payable emission intensity_Net zero'] * rate * 125
		elif row['year_act'] > 2025:
			result.loc[index, 'carbon cost_Net zero scenario'] = row['Payable emission intensity_Net zero'] * rate * 170
	# Adjust for years 2055 and 2060 for Net Zero Scenario
	for index, row in result.iterrows():
		if row['year_act'] > 2050:
			value_to_assign = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2050), 
				'carbon cost_Net zero scenario'
			].values
			if len(value_to_assign) > 0:
				result.at[index, 'carbon cost_Net zero scenario'] = value_to_assign[0]
	# Merge with fix_cost data for Net Zero Scenario
	data_fixcost = pd.read_excel(data_file_path, sheet_name='fix_cost')
	NetZero_merged_data = pd.merge(
		data_fixcost, 
		result[['technology', 'year_act', 'carbon cost_Net zero scenario']],
		left_on=['technology', 'year_act'],
		right_on=['technology', 'year_act'],
		how='left'
	)
	NetZero_merged_data['value'] = NetZero_merged_data['value'] + NetZero_merged_data['carbon cost_Net zero scenario'].fillna(0)
	NetZero_merged_data.drop(columns=['carbon cost_Net zero scenario'], inplace=True)
	# Reintegrate the updated fix_cost data into the scenario
	for index, row in NetZero_merged_data.iterrows():
		scenario.add_par('fix_cost', {
			'node_loc': 'Alberta',
			'technology': row['technology'],
			'year_vtg': row['year_act'],
			'year_act': row['year_act'],
			'mode': 'standard',
			'unit': 'USD/kWyr',
			'value': row['value']
		})


def apply_obps(scenario, data_file_path='data/obps_inputs_clean.xlsx'):
	"""
	Apply the Output-Based Pricing System (OBPS) policy for the Baseline Canada Scenario
	to the given MESSAGEix scenario.
	This function modifies the scenario's fixed costs based on emissions intensity and carbon pricing.
	Args:
		scenario (ixmp.Scenario): The MESSAGEix scenario to apply the OBPS policy to.
		data_file_path (str): Path to the Excel file containing necessary data.
	"""
	# Read the required data
	data_relation = pd.read_excel(data_file_path, sheet_name='Merged_Sheet')

	# Now you have a dataframe with the correct units which is for Standard, it would be tc/KW or tonne of carbon per Kwyr. 

	rel_co2cc = scenario.par('relation_activity', filters = {'relation':'CO2_CC'})
	tecs_co2cc = rel_co2cc['technology'].unique()
	provinces = scenario.set('node')[2:]
	
	#data_relation = data_relation[data_relation["region"].isin(provinces)]
	tightening_rates = data_relation[data_relation["variable"].str.contains("Tightening")]
	standards = data_relation[data_relation["variable"].str.contains("Standard")]
	merged_df = standards.merge(tightening_rates, on=["technology", "region", "time"], suffixes=("_from_tr", "_from_std"))
	
	def multiply_values(row):
		# NOTE: apply provinvial tightening rate when possible, otherwise apply the national tightening rate
		if row['value_from_tr'] == 0:
			# Find the value for 'Canada' with the same 'time' and 'technology'
			canada_value = merged_df[(merged_df['region'] == 'Canada') &
									 (merged_df['time'] == row['time']) &
									 (merged_df['technology'] == row['technology'])]['value_from_tr'].values[0]
			return row['value_from_std'] * canada_value
		else:
			return row['value_from_tr'] * row['value_from_std']

	merged_df["final_value"] = merged_df.apply(multiply_values, axis=1)
	'''
	for std in standards.iterrows():
		for tr in tightening_rates.iterrows():
			if std[1].loc["technology"] in tecs_co2cc and std[1].loc["region"] != "Canada":
				if std[1].loc["region"] == tr[1].loc["region"] and std[1].loc["technology"] == tr[1].loc["technology"] and std[1].loc["time"] == tr[1].loc["time"]:
					obps_rate['value'] = std[1].loc["value"] * tr[1].loc["value"]
					obps_rate['region'] = std[1].loc["region"]
					obps_rate['variable'] = std[1].loc["variable"]
					obps_rate['technology'] = std[1].loc["technology"]
					obps_rate['year_vtg'] = std[1].loc["time"]
					obps_rate['unit [tCO2/-]'] = "KWa"

			
			#TODO for MA to figure what if they're in both, then which ones to apply


			elif data_relation['variable'].str.contains('Tightening'):	
				# Define conditions for filtering the data

				rel_co2emi = scenarip.par('relation_activity'. filters = {'relation':'CO2_Emission'})_
				tecs_co2emi = rel_co2emi['technology'].unique()

				# filter data relation with tecs_co2_emi and tecs_co2cc se[arateley ]





	# Filter the data based on the conditions
	result = data_relation[conditions_2][['technology', 'value', 'node_rel', 'year_act']]
	# Initialize columns for calculations
	result['Emission Intensity Reduction_baseline'] = 0.0
	# Calculate Emission Intensity Reduction_baseline
	for index, row in result.iterrows():
		if 2020 < row['year_act'] < 2055:
			previous_year_value = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == row['year_act'] - 5), 
				'Emission Intensity Reduction_baseline'
			].values
			if len(previous_year_value) > 0:
				result.loc[index, 'Emission Intensity Reduction_baseline'] += previous_year_value[0] + 3.33/100
	# Calculate Emission intensity standard_Baseline Canada Scenario
	result['Emission intensity standard_Baseline Canada Scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] > 2020:
			value_cal = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2015), 
				'value'
			]
			if not value_cal.empty:
				result.at[index, 'Emission intensity standard_Baseline Canada Scenario'] = row['value'] - row['Emission Intensity Reduction_baseline'] * value_cal.values[0]
			else:
				value_cal = result.loc[
					(result['technology'] == row['technology']) & 
					(result['year_act'] == 2020), 
					'value'
				]
				result.at[index, 'Emission intensity standard_Baseline Canada Scenario'] = row['value'] - row['Emission Intensity Reduction_baseline'] * value_cal.values[0]
	# Calculate Payable emission intensity_Baseline scenario
	result['Payable emission intensity_Baseline scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] > 2020:
			result.loc[index, 'Payable emission intensity_Baseline scenario'] = row['value'] - row['Emission intensity standard_Baseline Canada Scenario']
	# Calculate carbon cost_Baseline Canada scenario
	rate = 0.73
	result['carbon cost_Baseline Canada scenario'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] == 2025:
			result.loc[index, 'carbon cost_Baseline Canada scenario'] = row['Payable emission intensity_Baseline scenario'] * rate * 125
		elif row['year_act'] > 2025:
			result.loc[index, 'carbon cost_Baseline Canada scenario'] = row['Payable emission intensity_Baseline scenario'] * rate * 170
	# Adjust for years 2055 and 2060
	for index, row in result.iterrows():
		if row['year_act'] > 2050:
			value_to_assign = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2050), 
				'carbon cost_Baseline Canada scenario'
			].values
			if len(value_to_assign) > 0:
				result.at[index, 'carbon cost_Baseline Canada scenario'] = value_to_assign[0]
	# Merge with fix_cost data and update the scenario's fix_cost
	data_fixcost = pd.read_excel(data_file_path, sheet_name='fix_cost')
	merged_data = pd.merge(
		data_fixcost, 
		result[['technology', 'year_act', 'carbon cost_Baseline Canada scenario']],
		left_on=['technology', 'year_act'],
		right_on=['technology', 'year_act'],
		how='left'
	)
	merged_data['value'] = merged_data['value'] + merged_data['carbon cost_Baseline Canada scenario'].fillna(0)
	merged_data.drop(columns=['carbon cost_Baseline Canada scenario'], inplace=True)
	# Reintegrate the updated fix_cost data into the scenario
	for index, row in merged_data.iterrows():
		scenario.add_par('fix_cost', {
			'node_loc': 'Alberta',
			'technology': row['technology'],
			'year_vtg': row['year_act'],
			'year_act': row['year_act'],
			'mode': 'standard',
			'unit': 'USD/kWyr',
			'value': row['value']
		})
	'''