#### MESSAGE_IX CANADA ####

# --- This script contains all the auxiliary functions to the model ---#

import os
import sys
import toml
import message_ix
import numpy as np
import pandas as pd

from typing import Optional, Tuple


def config_validation(config_path: str):
		"""
		Function to verify the MESSAGE config file

		Input: path to config.toml file
		Output: Error, or success messages

		Logic: only checking for missing fields, since additional settings won't hinder
		model execution, only missing settings will cause the model to fail
		"""
		validated = False

		try:
			with open(config_path, "r") as config_file:
				check_config = toml.load(config_file)
				print("Config file read successfully!")
		except FileNotFoundError:
			print(f"TOML config file not found in path {config_path}")
			sys.exit()
        # Using baseline scenario as a basis for validation
		sample_file = toml.load(os.path.join(os.getcwd(), 
                    "model/scenarios/baseline", "config.toml"))
		# Format verification
		for section, fields in sample_file.items():
			for field, sub_field in fields.items():
				# First check that all fields and sections are present in the config file
				if section not in check_config:
					raise Exception(
						f"Missing section '{section}' in config file '{config_path}'"
					)
				elif field not in check_config[section]:
					raise Exception(f"Missing field '{field}' in section '{section}'")

		print(
			f"{'#' * 100}\nConfig file '{config_path}' passed format verification!\n{'#' * 100}"
		)
		validated = True
		return validated

def clone_scenario(scenario_name: str, scenario_params: list, keep_solution=False) -> tuple:
		"""
		Clone an existing scenario
        Parameters:
            scenario_name (str): name of scenario to be cloned
            scenario_params: list of the necessary MESSAGE parameters to clone a scenario
                [0]: mp
                [1]: modelName
                [2]: scenarioName
                [3]: version
                [4]: annotation
        Returns: a copy of the input MESSAGE scenario
		"""

		scenario = message_ix.Scenario(
			scenario_params[0], scenario_params[1], scenario_params[2],
            version=scenario_params[3], annotation=scenario_params[4]
		)
		scenario_copy = scenario.clone(
			scenario_params[0],
			scenario_name,
			keep_solution=keep_solution,
		)

		return scenario_copy

def map_yv_ya_lt(
		periods: Tuple[int, ...], lt: int, ya: Optional[int] = None
	) -> pd.DataFrame:
		"""All meaningful combinations of (vintage year, active year) given periods.
		Parameters
		----------
		labels : pandas.DataFrame
						Each column (dimension) corresponds to one in df. Each row represents one
						matched set of labels for those dimensions.
		lt : int, lifetime
		"""
		if not ya:
			ya = periods[0]
			print(f"First active year set as {ya!r}")
		if not lt:
			raise ValueError("Add a fixed lifetime parameter 'lt'")
		# The following lines are the same as
		# message_ix.tests.test_feature_vintage_and_active_years._generate_yv_ya
		# - Create a mesh grid using numpy built-ins
		# - Take the upper-triangular portion (setting the rest to 0)
		# - Reshape
		data = np.triu(np.meshgrid(periods, periods, indexing="ij")).reshape((2, -1))
		# Filter only non-zero pairs
		df = pd.DataFrame(
			filter(sum, zip(data[0, :], data[1, :])),
			columns=["year_vtg", "year_act"],
			dtype=np.int64,
		)
		# Select values using the ya and lt parameters
		return df[(ya <= df.year_act) & (df.year_act - df.year_vtg <= lt)]

def map_learning_rate(l_rate: float, initial_cost: float, cost_type, years = []) -> pd.DataFrame:

	values = np.zeros(len(years))
	values[0] = initial_cost

	for i in range(1, len(years)):
		values[i] = values[i-1] * l_rate

	if cost_type is "investment":
		df = pd.DataFrame({"year_vtg": years "value": values}, dtype=np.float64)
	elif cost_type is "fixed":
		df = pd.DataFrame({"value": values}, dtype=np.float64)
     
	return df

def expand_grid(self, dictionary):
	"""
	Create a DataFrame from all combinations of dictionary values.
	Args:
		dictionary (dict): A dictionary where each key is a column name and the value is a list of column values.
	Returns:
		pd.DataFrame: A DataFrame containing all combinations of the provided values.
	"""
	return pd.DataFrame([row for row in product(*dictionary.values())], columns=dictionary.keys())

# Reporter method
def report_to_pyam(scenario, directory_path, output_path):
	"""
	Function to process all .xlsx files in a directory, extract region and scenario data,
	process the data for each sheet, and save the final dataframe as a CSV.
	Args:
		directory_path (str): Path to the directory containing .xlsx files.
		output_path (str): Path to save the resulting CSV file.
	Returns:
		final_df (pd.DataFrame): The concatenated dataframe from all processed .xlsx files.
	"""

	# Automatically list all .xlsx files in the directory
	file_paths = [os.path.join(directory_path, file) for file in os.listdir(directory_path) if file.endswith('.xlsx')]
	dfs = []
	# Process each file
	for file in file_paths:
	# Extract region and scenario from the file name
		file_name = os.path.basename(file)

		# Split file name using '__' to handle sections like baseline, version, and region
		parts = file_name.split('__')

		# Extract scenario, including the version, but without '__' (e.g., 'baseline v4')
		scenario = f"{parts[1]} {parts[2].split('_')[0]}"  # Extract 'baseline' and 'v4', separated by a space

		# Extract region from the part after 'v4_'
		region = parts[2].split('_')[1].split('.')[0]  # Extract region (e.g., 'PrinceEdwardIsland')

		# Open the Excel file and get sheet names
		xls = pd.ExcelFile(file)
		sheet_names = xls.sheet_names
		for sheet in sheet_names:
			df = pd.read_excel(file, sheet_name=sheet)
			# Process variable and unit from the sheet name
			variable, unit = sheet.split(' (')
			variable = variable.strip()  # Strip spaces from variable
			unit = unit.strip().rstrip(')')  # Strip spaces from unit and remove closing parenthesis
			# Rename the first column to 'time'
			df.rename(columns={df.columns[0]: 'time'}, inplace=True)
			# Melt the dataframe to have 'time' as id_vars, variable names in 'variable', and values in 'value'
			df = pd.melt(df, id_vars=['time'], var_name='variable', value_name='value')
			# Add the unit and processed variable names
			df['unit'] = unit
			df['variable'] = variable + '|' + df['variable']
			# Add region and scenario columns
			df['region'] = region
			df['scenario'] = scenario
			df['model'] = 'MESSAGEix-Canada'
			# Append the dataframe to the list
			dfs.append(df)
	# Concatenate all dataframes into a single dataframe
	final_df = pd.concat(dfs, ignore_index=True)
	# Filter the dataframe to only include data from 2020 onwards
	final_df = final_df[final_df['time'] >= 2020]
	# Save the final dataframe to a CSV file
	final_df.to_csv(output_path, index=False)
	return final_df