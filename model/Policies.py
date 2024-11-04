import pandas as pd
import numpy as np
import pycountry
import message_ix
import time

from pathlib import Path
from geotext import GeoText
from itertools import product
from message_ix_models.util import (
	broadcast,
	same_node,
)
from model.Model import model_MSG
from model.utils import clone_scenario

class policies_MSG(model_MSG):
	def __init__(self, scenario_name: str, params: list):
		#super().__init__(scenario_name=scenario)
		self._scenario = clone_scenario(scenario_name, params, False)
	   
	def expand_grid(self, dictionary):
		"""
		Create a DataFrame from all combinations of dictionary values.

		Args:
			dictionary (dict): A dictionary where each key is a column name and the value is a list of column values.

		Returns:
			pd.DataFrame: A DataFrame containing all combinations of the provided values.
		"""
		return pd.DataFrame([row for row in product(*dictionary.values())], columns=dictionary.keys())

	def bound_emissions(self, msgSDG, nodeName):
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
		df = self.expand_grid(dic)
		df = df.iloc[0:9]  # Select the first 9 rows
		df['type_year'] = year_df

		# Add the parameter to the scenario and commit the changes
		msgSDG.add_par('bound_emission', df)
		msgSDG.commit('emissions bounded')

	def carbon_price(self):
		pass
	
	def CER(self):
		pass
	
	def coal_phase_out(self, province, nodes_tax):
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
		technologies = self.scenario.set('technology')

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
		coal_phase_yrs = self.scenario.set('year')[16:]

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
		self.scenario.check_out()
		existing_df = self.scenario.par('bound_activity_up')
		self.scenario.remove_par('bound_activity_up', existing_df)
		self.scenario.add_par('bound_activity_up', filtered_df)
		self.scenario.commit('Coal phase-out implemented.')

	def add_federal_carbon_tax(self):
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
	
	def add_investment_tax_credit(self):
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
	
	def apply_obps_baseline(self, data_file_path: str):
		"""
		Apply the Output-Based Pricing System (OBPS) policy for the Baseline Canada Scenario
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
			self.scenario.add_par('fix_cost', {
				'node_loc': 'Alberta',
				'technology': row['technology'],
				'year_vtg': row['year_act'],
				'year_act': row['year_act'],
				'mode': 'standard',
				'unit': 'USD/kWyr',
				'value': row['value']
			})

	def apply_obps_netzero(self, data_file_path: str):
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
			self.scenario.add_par('fix_cost', {
				'node_loc': 'Alberta',
				'technology': row['technology'],
				'year_vtg': row['year_act'],
				'year_act': row['year_act'],
				'mode': 'standard',
				'unit': 'USD/kWyr',
				'value': row['value']
			})

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
	
	def add_policy_for_province(self):
		"""
		Add policies related to Yukon to a MESSAGEix scenario.

		This function modifies the provided MESSAGEix scenario to include specific energy policies 
		related to the Yukon province. The specific implementation details of these policies, 
		such as the types of policies, the affected sectors, and the time period for implementation, 
		should be added within this function.

		Args:
			scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the Yukon policies will be added.

		Returns:
			None
		"""
		pass
	
	def shares(self, msgSDG, path, nodeName, suffix):
		"""
		Add share constraints for renewable energy technologies in a MESSAGEix scenario.

		This function modifies the provided MESSAGEix scenario to include share constraints for renewable energy 
		technologies. It sets up the necessary sets and parameters to define the shares for renewable electricity 
		technologies.

		Args:
			msgSDG (MESSAGEix.Scenario): The MESSAGEix scenario object to be modified.
			path (str): The path to the directory containing the input Excel file.
			nodeName (str): The name of the node for which the shares are being defined.
			suffix (str): The suffix for the input Excel file name.

		Returns:
			None
		"""
		msgSDG.check_out()

		# Add type_tec for renewable
		type_tec = 'renewable_electr'
		msgSDG.add_set('type_tec', type_tec)

		# Define share for renewable
		shares = 'share_renew_electr'
		msgSDG.add_set('shares', shares)

		# Include technologies for which shares need to be defined
		tec = ('wind_ppf', 'wind_ppl', 'solar_pv_ppl', 'solar_th_ppl', 'hydro_lc', 'hydro_hc')
		msgSDG.add_set('cat_tec', pd.DataFrame({'type_tec': type_tec, 'technology': tec}))

		# Mapping total share from which share is intended
		dic = {
			'shares': [shares],
			'node_share': [nodeName],
			'node': [nodeName],
			'type_tec': ['powerplant'],
			'mode': ['M1'],
			'commodity': ['electr'],
			'level': ['secondary']
		}
		df = self.expand_grid(dic)
		msgSDG.add_set('map_shares_commodity_total', df)

		# Mapping share from total
		dic = {
			'shares': [shares],
			'node_share': [nodeName],
			'node': [nodeName],
			'type_tec': [type_tec],
			'mode': ['M1'],
			'commodity': ['electr'],
			'level': ['secondary']
		}
		df = self.expand_grid(dic)
		msgSDG.add_set('map_shares_commodity_share', df)

		# Importing required shares from Excel files
		xls_par = pd.ExcelFile(f"{path}/Parameters{suffix}.xlsx")
		sheet_shares = xls_par.parse('share_comodity_lo')
	
		msgSDG.add_par('share_commodity_lo', sheet_shares)
		msgSDG.commit('renewable shares defined')

		# TODO: Check the level at which shares need to be defined, usually electricity, a good level is secondary.

	def change_technology_cost(self):
		"""
		Change the cost of technologies in a MESSAGEix scenario     
		This function modifies the provided MESSAGEix scenario to change the costs of specified technologies. 
		The specific implementation details, such as the technologies affected, the new cost values, 
		and the time periods for the cost changes, should be added within this function     
		Args:
			scenario (MESSAGEix.Scenario): The MESSAGEix scenario for which the technology costs will be changed        
		Returns:
			None
		"""
		pass 
	
	def generate_policies(self, solve=False):
		
		script_dir = Path(__file__).resolve().parent
		scenario_folder = script_dir / self.config["data"]["scenario_folder"]
		caseName = (
			self.scenario.model
			+ "__"
			+ self.scenario.scenario
			+ "__v"
			+ str(self.scenario.version)
		)

		if self.apply_obps_netzero: # add OBPS to netzero scenario
			path_to_obps_data = script_dir / scenario_folder
			self.apply_obps_netzero(data_file_path=path_to_obps_data)
		elif self.apply_obps_baseline: # add OBPS to baseline scenario
			path_to_obps_data = script_dir / scenario_folder
			self.apply_obps_baseline(data_file_path=path_to_obps_data)
		
		if solve: # solve scenario again with policies added
			start = time.time()
			try:
				self.scenario.solve(
					solve_options={"barcrossalg": "2", "lpmethod": "1"}, case=caseName
				)
				end = time.time()
				print(
					f"\n==================================================\n\
				Solving process time: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec\
				\n=================================================="
				)

			except Exception as solve_error:
				print(f"Scenario {caseName} did not solve because of the following exception:\n{solve_error}\n")
		
		return self.scenario