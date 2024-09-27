#### MESSAGE_IX CANADA ####

# --- This script contains all the auxiliary functions to the model ---#

import os
import sys
import toml
import message_ix
import numpy as np
import pandas as pd

from typing import Optional, Tuple, Union


def config_validation(config_path: str, validated=False):
		"""
		Function to verify the MESSAGE config file

		Input: path to config.toml file
		Output: Error, or success messages

		Logic: only checking for missing fields, since additional settings won't hinder
		model execution, only missing settings will cause the model to fail
		"""
		if validated is True:
			return

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

