import pandas as pd
import numpy as np
import os
import sys
import toml
import yaml
import message_ix


class pre_process_message:

	def __init__(self, scenario: str):
		self.scenario = scenario
		self.sample_config = toml.load(os.path.join(os.getcwd(), "model/scenarios/common", "sample_config.toml"))
		self.scenario_path = os.path.join('model/scenarios', scenario)

	# Input processing functions

	def config_validation(self):
		'''
		Function to verify the COPPER config file
		
		Input: path to config.toml file
		Output: Error, or success messages
		
		Logic: only checking for missing fields, since additional settings won't hinder
		model execution, only missing settings will cause the model to fail
		'''
		file_path=os.path.join(self.scenario_path, 'config.toml')
		try:
			with open(file_path, 'r') as config_file:
				check_config = toml.load(config_file)
				print("Config file read successfully!")
		except FileNotFoundError:
			print(f"TOML config file not found in path {file_path}")
			sys.exit()
		sample_file = self.sample_config
		# Format verification
		for section, fields in sample_file.items():
			for field, sub_field in fields.items():
				# First check that all fields and sections are present in the config file
				if section not in check_config:
					raise Exception(f"Missing section '{section}' in config file '{file_path}'")
				elif field not in check_config[section]:
					raise Exception(f"Missing field '{field}' in section '{section}'")
		print(f"{'#' * 100}\nConfig file '{file_path}' passed format verification!\n{'#' * 100}")
	
	def add_technology(techs_file: str):
		'''
		Function to add new technologies to the model
		
		Input: path to technology YAML file
		Output: None
		
		Logic: Creates the corresponding technology inside MESSAGE
		'''
		# Read file from path and convert to dictionary
		with open(techs_file) as data:
			technologies = yaml.load(data)
	
		return technologies
			

	
	