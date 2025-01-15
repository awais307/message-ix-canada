#### MESSAGE_IX CANADA ####

# --- This script contains the Main model's class ---#


# Including all necessary imports
import message_ix
import ixmp
import toml
import yaml
import os
import time
import pandas as pd
import pyam
import warnings
from model.policies.hydrogen_shares import add_hydrogen_shares
from model.utlities.pop_gdp import process_gdp_population_data, add_population_gdp_to_scenario
from model.utlities.demands import adjust_demands
from model.utlities.report import generate_report
from model.utlities.historical_activity import balance_import_export, update_historical_activity

from message_ix_models.util import (
	broadcast,
	make_matched_dfs,
	same_node,
	same_time,
)
from scipy.optimize import linprog
from pathlib import Path
from typing import Union
from model.utils import (map_yv_ya_lt, config_validation, map_learning_rate)
from message_ix_models.report.legacy.iamc_report_hackathon import report

warnings.filterwarnings("ignore")  # Ignore warnings to keep the output clean

class model_MSG:
	"""
	model_MSG class provides methods to process and validate configuration files,
	map vintage and active years, add technologies, adjust demands, and handle
	GDP and population data for a MESSAGEix scenario.

	Methods
	-------
	__init__(self, scenario_name: str)
			Initializes the model_MSG class with the given scenario name and loads
			configuration files.

	config_validation(self, validated=False)
			Validates the MESSAGE config file by checking for missing fields.

	map_yv_ya_lt(self, periods: Tuple[int, ...], lt: int, ya: Optional[int] = None) -> pd.DataFrame
			Generates all meaningful combinations of (vintage year, active year) given periods.

	add_technology(self, techs_file: str)
			Adds new technologies to the model based on the provided technology YAML file.

	add_hydrogen_shares(self, path: Union[str, Path])
			Adds hydrogen shares to a MESSAGEix scenario using data from an Excel file.

	process_gdp_population_data(self, path_to_gdp: Union[str, Path], path_to_pop: Union[str, Path]) -> pd.DataFrame
			Processes GDP and population data for the model and returns a DataFrame with
			processed data.

	adjust_demands(self)
			Adjusts demands in the scenario based on population and GDP data.

	add_population_gdp_to_scenario(self, population_data: pd.DataFrame, gdp_data: pd.DataFrame)
			Adds processed population and GDP data to the scenario.
	"""

	def __init__(self, scenario_name: str):
		"""
		Initialize the scenario with the given name.

		Args:
				scenario_name (str): The name of the scenario to initialize.

		Attributes:
				scenario (str): The name of the scenario.
				sample_config (dict): The configuration loaded from the baseline config.toml file.
				scenario_path (str): The path to the scenario directory.
				config_path (str): The path to the scenario's config.toml file.
				config (dict): The configuration loaded from the scenario's config.toml file.
		"""
		self.scenario = scenario_name
		self.sample_config = toml.load(
			os.path.join(os.getcwd(), "model/scenarios/baseline", "config.toml")
		)
		self.scenario_path = os.path.join("model/scenarios", scenario_name)
		self.config_path = os.path.join(self.scenario_path, "config.toml")
		self.config = toml.load(self.config_path)
		
		self.modelName = self.config["general"]["model_name"]
		self.scenarioName = self.config["general"]["scenario_name"]
		self.platform_name = self.config["general"]["ix_platform"]
		self.version = self.config["general"]["version"]
		self.annotation = self.config["general"]["annotation"]
		self.process_historical = self.config["pre_process"]["process_historical_data"]
		self.add_hydrogen_shares_f = self.config["pre_process"]["add_hydrogen_shares"]
		self.add_obps_baseline = self.config["policies"]["apply_obps_baseline"]
		self.add_obps_netzero = self.config["policies"]["apply_obps_netzero"]
		self.new_reporter = self.config["post_process"]["generate_new_reporter_output"]
		self.legacy_reporter = self.config["post_process"]["generate_legacy_reporter_output"]
		self.solve = self.config["model"]["solve"]
		self.to_excel = self.config["post_process"]["export_to_xlsx"]
		self.add_techs = self.config["pre_process"]["add_technology"]["add_techs"]
		self.mp = ixmp.Platform(name=self.platform_name, jvmargs=['-Xmx16G'])

	## Scenario creation functions ##
	def add_technology(
		self,
		techs_file: str,
	):
		"""
		Function to add new technologies to the model

		Input: path to technology YAML file
		Output: None

		Logic: Creates the corresponding technology inside MESSAGE
		"""
		self.scenario.check_out()

		tech_config = self.config["pre_process"]["add_technology"]

		years = self.scenario.set("year").astype(int).to_list()[14:]
		first_year = self.scenario.firstmodelyear

		# Read file from path and convert to dictionary
		with open(techs_file) as data:
			technologies = yaml.safe_load(data)
			for tech, tech_data in technologies.items():
				if tech in tech_config["techs"]:
					self.scenario.add_set("technology", tech)

					if tech_data["node_select"] == "all":
						provinces = self.scenario.set("node").to_list()[2:]
					elif tech_data["node_select"] == "custom":
						provinces = tech_data["provinces"]
					else:
						raise Exception(
							f"Option {tech_data['node_select']} not recognized."
							+ "Options for node_selct in technology.yaml is either 'all' or 'custom'"
						)

					# Creating DFs

					# input dataframe
					input_df = (
						message_ix.make_df(
							"input",
							# node_loc=provinces,
							technology=tech,
							mode=tech_data["mode"],
							commodity=tech_data["commodity"][0]["input"][0]["com_name"],
							level=tech_data["commodity"][0]["input"][2]["com_level"],
							time=tech_data["time"],
							time_origin=tech_data["time"],
							value=tech_data["commodity"][0]["input"][1]["com_value"],
							unit=tech_data["unit"][1]["energy"],
						)
						.pipe(
							broadcast,
							map_yv_ya_lt(
								years, tech_data["tec_lifetime"], first_year
							),
							# time=tech_data["time"],
							node_loc=provinces,
						)
						.pipe(same_node)
						.pipe(same_time)
					)
					self.scenario.add_par("input", input_df)

					# output dataframe
					output_df = (
						message_ix.make_df(
							"output",
							# node_loc=provinces,
							technology=tech,
							mode=tech_data["mode"],
							commodity=tech_data["commodity"][1]["output"][0][
								"com_name"
							],
							level=tech_data["commodity"][1]["output"][2]["com_level"],
							time=tech_data["time"],
							time_origin=tech_data["time"],
							value=tech_data["commodity"][1]["output"][1]["com_value"],
							unit=tech_data["unit"][1]["energy"],
						)
						.pipe(
							broadcast,
							map_yv_ya_lt(
								years, tech_data["tec_lifetime"], first_year
							),
							# time=tech_data["time"],
							node_loc=provinces,
						)
						.pipe(same_node)
						.pipe(same_time)
					)
					self.scenario.add_par("output", output_df)

					# variable cost
					var_cost_df = message_ix.make_df(
						"var_cost",
						node_loc=provinces,
						technology=tech,
						mode=tech_data["mode"],
						value=tech_data["var_cost_2020"][1]["cost_value"],
						time=tech_data["time"],
						unit=tech_data["unit"][0]["cost"],
					).pipe(
						broadcast,
						map_yv_ya_lt(years, tech_data["tec_lifetime"], first_year),
					)
					self.scenario.add_par("var_cost", var_cost_df)

										# fixed cost
					fix_cost_df = message_ix.make_df(
						"fix_cost",
						node_loc=provinces,
						technology=tech,
						#value=tech_data["fix_cost_2020"][1]["cost_value"],
						time=tech_data["time"],
						unit=tech_data["unit"][0]["cost"],
					).pipe(broadcast, map_yv_ya_lt(years, 
                                    tech_data["tec_lifetime"], first_year),
					).pipe((map_learning_rate, 'input_df'),
							provinces=provinces,
            				l_rate=tech_data["fixed_cost_lr"], 
							initial_cost=tech_data["fix_cost_2020"][1]["cost_value"], 
    						cost_type="fixed", years=years, tech_lifetime=tech_data["tec_lifetime"]
        			)
					self.scenario.add_par("fix_cost", fix_cost_df)

					# investment cost
					inv_cost_df = message_ix.make_df(
						"inv_cost",
						node_loc=provinces,
						technology=tech,
						#year_vtg=years,
						level=tech_data["inv_cost_2020"][0]["cost_level"],
						#value=tech_data["inv_cost_2020"][1]["cost_value"],
						time=tech_data["time"],
						unit=tech_data["unit"][0]["cost"],
					).pipe(broadcast, map_learning_rate(provinces=provinces,initial_cost=tech_data["inv_cost_2020"][1]["cost_value"], l_rate=tech_data["investment_lr"], cost_type="investment", years=years, tech_lifetime=tech_data["tec_lifetime"]))
					inv_cost_df["year_vtg"] = inv_cost_df["year_vtg"].astype(int)
					self.scenario.add_par("inv_cost", inv_cost_df)

					# emission factor
					emission_factor_df = message_ix.make_df(
						"emission_factor",
						node_loc=provinces,
						technology=tech,
						mode=tech_data["mode"],
						value=tech_data["emission_factor"],
						emission=tech_data["emission_type"],
						unit="-",
					).pipe(
						broadcast,
						map_yv_ya_lt(years, tech_data["tec_lifetime"], first_year),
					)
					self.scenario.add_par("emission_factor", emission_factor_df)

					# construction time
					for i, j in zip(
						tech_data["commodity"][1]["output"][1]["com_value"],
						tech_data["commodity"][0]["input"][1]["com_value"],
					):
						tec_construction_df = make_matched_dfs(
							input_df,
							capacity_factor=tech_data["capacity_factor"],
							technical_lifetime=tech_data["tec_lifetime"],
							construction_time=tech_data["construction_time"],
						)
						self.scenario.add_par(
							"capacity_factor", tec_construction_df["capacity_factor"]
						)
						self.scenario.add_par(
							"technical_lifetime",
							tec_construction_df["technical_lifetime"],
						)
						self.scenario.add_par(
							"construction_time",
							tec_construction_df["construction_time"],
						)

			self.scenario.commit("Technologies added successfully")
	
	def add_hydrogen_shares(self, path: Union[str, Path]):
		"""
		Add hydrogen shares to a MESSAGEix scenario.

		This function modifies the provided MESSAGEix scenario to include hydrogen shares.
		The specific implementation details, such as the hydrogen share percentages and the affected sectors,
		should be added within this function.

		Args:
						path (str or Path): Path to the Excel file containing hydrogen share data.

		Returns:
						None

		Logic: adds hydrogen shares to the MESSAGEix scenario
		"""
		add_hydrogen_shares(self, path)

	def process_gdp_population_data(
		self, path_to_gdp: Union[str, Path], path_to_pop: Union[str, Path]
	):
		"""
		Process GDP and population data for the model.

		Args:
						path_to_pop (str or Path): Path to the CSV file containing raw population data.
						path_to_gdp (str or Path): Path to the CSV file containing raw GDP data.

		Returns:
						pd.DataFrame: DataFrame containing processed GDP, population, and GDP per capita data for each province.
		"""
		return process_gdp_population_data(path_to_gdp, path_to_pop)
	
	def adjust_demands(self):
		"""
		Adjust demands in the scenario based on population and GDP data.

		Args:
						None

		Returns:
						pd.DataFrame: DataFrame containing updated demand data.
		"""
		return adjust_demands(self)
		
	def add_population_gdp_to_scenario(
		self, population_data: pd.DataFrame, gdp_data: pd.DataFrame
	):
		"""
		Add processed population and GDP data to the scenario.

		Args:
						population_data (pd.DataFrame): DataFrame containing processed population data.
						gdp_data (pd.DataFrame): DataFrame containing processed GDP data.

		Logic:
						Adds the processed population and GDP data to the scenario's 'bound_activity_lo' parameter.
		"""
		add_population_gdp_to_scenario(self, population_data, gdp_data)

	def update_historical_activity(self, path: Union[str, Path]):
		"""
		Update the historical activity parameter in the scenario with data from a specified path.

		Args:
						path (str or Path): Path to the historical activity data.
		"""
		update_historical_activity(self, path)
	
	def balance_import_export(self, historical_activity: pd.DataFrame):
		"""
		Balance energy production, import, and export for each province and year.

		Args:
						historical_activity (pd.DataFrame): DataFrame containing historical activity data for each province and year.

		Returns:
						pd.DataFrame: DataFrame with balanced import and export values.
		"""
		return balance_import_export(self, historical_activity)

	def generate_report(
		self,
		output_path="scenarios/baseline/MESSAGE_test.csv",
		min_year=2015,
		max_year=2060,
		from_excel=False,
		unit_correct=True,
	):
		"""
		Generate a report from the MESSAGEix scenario and save it to a CSV file.

		Args:
						output_path (str): The path where the output CSV file will be saved.
						min_year (int): The minimum year for the report.
						max_year (int): The maximum year for the report.
						from_excel (bool): Whether to read the report from an Excel file.
						unit_correct (bool): Whether to correct units in the report.
		"""
		generate_report(
			self,
			output_path,
			min_year,
			max_year,
			from_excel,
			unit_correct)

	#TODO move to policies/
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
	
	# Full scenario set-up
	def setup_scenario(self) -> tuple:
		"""
		Set up, initialize, and solve a MESSAGEix scenario based on the provided configuration.

		This function reads a configuration file for a given scenario, initializes a
		MESSAGEix scenario object, and performs pre-processing steps as defined in the
		configuration. The function returns the platform and scenario objects for further use.

		Args:
						None

		Returns:
						tuple: A tuple containing the ixmp.Platform object and the message_ix.Scenario object.

		"""

		# Config verification:
		config_validation(self.config_path)

		# Scenario set-up
		start = time.time()
		
		# TODO add option for SSP
		# ssp = 'SSP2'

		self.scenario = message_ix.Scenario(
		self.mp, self.modelName, self.scenarioName, version=self.version, annotation=self.annotation
		)

		caseName = (
			self.scenario.model
			+ "__"
			+ self.scenario.scenario
			+ "__v"
			+ str(self.scenario.version)
		)

		script_dir = Path(__file__).resolve().parent
		scenario_folder = script_dir / self.config["data"]["scenario_folder"]
		excel_path = script_dir / self.config["data"]["provincial_input_file"]
		# Update message scenario
		self.scenario.read_excel(
			excel_path, add_units=True, commit_steps=False, init_items=True
		)

		if self.process_historical:
			self.update_historical_activity(path=scenario_folder)

		if self.add_hydrogen_shares_f:
			path_to_hydrogen_data = script_dir / scenario_folder
			self.add_hydrogen_shares(path=path_to_hydrogen_data)

		
		# Technologies
		if self.add_techs:
			self.add_technology(techs_file=f"{scenario_folder}/technology.yaml")

		# Set-up policies
		if self.add_obps_netzero:
			path_to_obps_data = script_dir / scenario_folder
			OBPS.apply_obps_netzero(scenario=self.scenario, data_file_path=path_to_obps_data)
		elif self.add_obps_baseline:
			path_to_obps_data = script_dir / scenario_folder
			OBPS.apply_obps(scenario=self.scenario)

  
		end = time.time()
		print(
			f"\n==================================================\n\
		Model creation time: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec \
		\n=================================================="
		)
		
		if self.solve:
			start = time.time()
			try:
				print("Solving the model...\n")
				self.scenario.solve(
					solve_options={"barcrossalg": "2", "lpmethod": "1", "threads": 20}, case=caseName
				)
				end = time.time()
				print(
					f"\n==================================================\n\
				Solving process time: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec\
				\n=================================================="
				)

			except Exception as solve_error:
				print(f"Scenario {caseName} did not solve because of the following exception:\n{solve_error}\n")

			if self.new_reporter:
				start = time.time()
				self.generate_report(
					output_path=f"model/output/{caseName}_new_reporter.csv",
					min_year=2020,
					max_year=2060,
					from_excel=False,
					unit_correct=True,
				)
				end = time.time()
				print(
					f"\n==================================================\n\
				Reporting with NEW reporter. Process time: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec\
				\n=================================================="
				)
			elif self.legacy_reporter:
				start = time.time()
				report(mp=self.mp, scen=self.scenario, out_dir="model/output")
				end = time.time()
				print(
					f"\n==================================================\n\
				Reporting with LEGACY reporter. Process time: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec\
				\n=================================================="
				)

		if self.to_excel:
			start = time.time()
			self.scenario.to_excel(f"{caseName}.xlsx")
			print(f"Exported Scenario to Excel: {caseName}.xlsx")
			end = time.time()
			print(
					f"\n==================================================\n\
				Exported results to Excel in: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec\
				\n=================================================="
				)

		return self.mp, self.scenario, scenario_folder
