#### MESSAGE_IX CANADA ####

# --- Script to contain classes for pre and postprocessing the model ---#

import itertools
import logging
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Optional, Tuple, Union

import ixmp
import matplotlib.pyplot as plt
import message_ix
import numpy as np

import pandas as pd
import pyam
import toml
import yaml
from matplotlib.backends.backend_pdf import PdfPages
from message_ix_models.util import (
    broadcast,
    make_matched_dfs,
    same_node,
    same_time,
)
from scipy.optimize import linprog

from model.policies.obps import apply_obps_baseline, apply_obps_netzero


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
                config_file (dict): The configuration loaded from the scenario's config.toml file.
        """
        self.scenario = scenario_name
        self.sample_config = toml.load(
            os.path.join(os.getcwd(), "model/scenarios/baseline", "config.toml")
        )
        self.scenario_path = os.path.join("model/scenarios", scenario_name)
        self.config_path = os.path.join(self.scenario_path, "config.toml")
        self.config_file = toml.load(self.config_path)
        ## Input processing functions ##

    def config_validation(self, validated=False):
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
            with open(self.config_path, "r") as config_file:
                check_config = toml.load(config_file)
                print("Config file read successfully!")
        except FileNotFoundError:
            print(f"TOML config file not found in path {self.config_path}")
            sys.exit()
        sample_file = self.sample_config
        # Format verification
        for section, fields in sample_file.items():
            for field, sub_field in fields.items():
                # First check that all fields and sections are present in the config file
                if section not in check_config:
                    raise Exception(
                        f"Missing section '{section}' in config file '{self.config_path}'"
                    )
                elif field not in check_config[section]:
                    raise Exception(f"Missing field '{field}' in section '{section}'")

        print(
            f"{'#' * 100}\nConfig file '{self.config_path}' passed format verification!\n{'#' * 100}"
        )
        validated = True
        return validated

    def map_yv_ya_lt(
        self, periods: Tuple[int, ...], lt: int, ya: Optional[int] = None
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

        tech_config = self.config_file["pre_process"]["add_technology"]

        years = self.scenario.set("year").to_list()[14:]
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
                            self.map_yv_ya_lt(
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
                            self.map_yv_ya_lt(
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
                        self.map_yv_ya_lt(years, tech_data["tec_lifetime"], first_year),
                    )
                    self.scenario.add_par("var_cost", var_cost_df)

                    # fixed cost
                    fix_cost_df = message_ix.make_df(
                        "fix_cost",
                        node_loc=provinces,
                        technology=tech,
                        value=tech_data["fix_cost_2020"][1]["cost_value"],
                        time=tech_data["time"],
                        unit=tech_data["unit"][0]["cost"],
                    ).pipe(
                        broadcast,
                        self.map_yv_ya_lt(years, tech_data["tec_lifetime"], first_year),
                    )
                    self.scenario.add_par("fix_cost", fix_cost_df)

                    # investment cost
                    inv_cost_df = message_ix.make_df(
                        "inv_cost",
                        # node_loc=provinces,
                        technology=tech,
                        year_vtg=years,
                        level=tech_data["inv_cost_2020"][0]["cost_level"],
                        value=tech_data["inv_cost_2020"][1]["cost_value"],
                        time=tech_data["time"],
                        unit=tech_data["unit"][0]["cost"],
                    ).pipe(broadcast, node_loc=provinces)

                    self.scenario.add_par("inv_cost", inv_cost_df)

                    # construction time
                    for i, j in zip(
                        tech_data["commodity"][1]["output"][1]["com_value"],
                        tech_data["commodity"][0]["input"][1]["com_value"],
                    ):
                        tec_construction_df = make_matched_dfs(
                            input_df,
                            capacity_factor=i / j,
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

        # Checkout the scenario for editing
        self.scenario.check_out()

        # Resolve the path to the hydrogen shares Excel file
        path = Path(path)
        # if not path.endswith(".xlsx"):
        # 	raise Exception("File provided for hydrogen shares is not in Excel format.")
        # else:
        data = pd.ExcelFile(path / "hydrogen_shares.xlsx")

        # Loop through each sheet in the Excel file
        for sheet_name in data.sheet_names:
            # Read the current sheet into a DataFrame
            df = pd.read_excel(path / "hydrogen_shares.xlsx", sheet_name=sheet_name)
            print(f"Sheet name: {sheet_name}")

            # Check if the sheet name corresponds to a set in the scenario
            if sheet_name in self.scenario.set_list():
                # Skip 'cat_tec' as it should not be modified
                if sheet_name == "cat_tec":
                    continue
                print("sets", sheet_name)

                # Add data to the set; handle 'type_tec' and 'shares' specifically
                if sheet_name in ["type_tec", "shares"]:
                    self.scenario.add_set(sheet_name, df[sheet_name])
                else:
                    self.scenario.add_set(sheet_name, df)

            # Check if the sheet name corresponds to a parameter in the scenario
            elif sheet_name in self.scenario.par_list():
                self.scenario.add_par(sheet_name, df)
                print("par", sheet_name)

        # Commit the changes to the scenario with a descriptive message
        self.scenario.commit("Updated scenario to include hydrogen shares")

        # Print the unique values of the 'shares' column in the 'share_commodity_lo' parameter
        print(self.scenario.par("share_commodity_lo")["shares"].unique())

        # Optional: Uncomment the line below to print the unique 'shares' values again
        # print(scenario.par("share_commodity_lo")['shares'].unique())

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
        # Resolve the full paths to the GDP and population data files
        path_to_gdp = Path(path_to_gdp).resolve()
        path_to_pop = Path(path_to_pop).resolve()

        # Read the CSV files containing GDP and population data into DataFrames
        ssp_gdp_df = pd.read_csv(path_to_gdp)
        ssp_pop_df = pd.read_csv(path_to_pop)

        # Convert population figures to consistent units (thousands to single units)
        ssp_pop_df["Population"] = ssp_pop_df["Population"] * 1000

        # Remove spaces from province names to ensure consistency
        ssp_pop_df["Province"] = ssp_pop_df["Province"].str.replace(" ", "")

        # Adjust specific province names for consistency
        province_mapping = {
            "Newfoundland and Labrador": "NewfoundlandandLabrador",
            "Prince Edward Island": "PrinceEdwardIsland",
        }
        ssp_pop_df["Province"] = ssp_pop_df["Province"].replace(province_mapping)

        # List of unique provinces from the GDP data
        provinces = ssp_gdp_df["Province"].unique()

        ssp_df = (
            []
        )  # Initialize an empty list to store the processed data for each province

        # Process each province's GDP and population data
        for province in provinces:
            # Filter GDP and population data for the current province
            c_ssp_gdp_df = ssp_gdp_df.loc[ssp_gdp_df.Province == province]
            c_ssp_pop_df = ssp_pop_df.loc[ssp_pop_df.Province == province]

            # Initialize empty lists to store GDP, population, and GDP per capita for each year
            gdp = []
            pop = []
            gdpc = []

            # Iterate over the years of interest to extract and calculate GDP per capita
            for jjj in [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]:
                if (
                    not c_ssp_gdp_df.loc[c_ssp_gdp_df.Year == jjj].empty
                    and not c_ssp_pop_df.loc[c_ssp_pop_df.Year == jjj].empty
                ):
                    gdp.append(
                        c_ssp_gdp_df.loc[c_ssp_gdp_df.Year == jjj, "GDP"].values[0]
                    )
                    pop.append(
                        c_ssp_pop_df.loc[c_ssp_pop_df.Year == jjj, "Population"].values[
                            0
                        ]
                    )
                    gdpc.append(gdp[-1] / pop[-1])  # Calculate GDP per capita
                else:
                    # If data is missing, append NaN to maintain the structure
                    gdp.append(np.nan)
                    pop.append(np.nan)
                    gdpc.append(np.nan)

            # Append the processed data for the current province to the list
            ssp_df.append(
                pd.DataFrame(
                    {
                        "year": [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060],
                        "gdp": gdp,
                        "pop": pop,
                        "gdpc": gdpc,
                        "iso": province,
                    }
                )
            )

        # Concatenate the data from all provinces into a single DataFrame
        ssp_df = pd.concat(ssp_df)
        return ssp_df  # Return the processed DataFrame

    def adjust_demands(self):
        """
        Adjust demands in the scenario based on population and GDP data.

        Args:
                        None

        Returns:
                        pd.DataFrame: DataFrame containing updated demand data.
        """

        # Define directories for data storage
        script_dir = Path(__file__).resolve().parent
        data_dir = script_dir / "../data"

        # File paths for GDP and population data
        gdp_data = data_dir / "gdp/gdp_messageca_prov.csv"
        population_data = data_dir / "population/pop_messageca_prov.csv"

        # Process GDP and population data for use in the scenario
        ssp_df = self.process_gdp_population_data(gdp_data, population_data)

        # Retrieve demand data from the scenario
        demand = self.scenario.par("demand")

        # Group demand data by specific columns and aggregate it at the 'Canada' level
        df_ca = (
            demand.groupby(["year", "commodity", "level", "time", "unit"])
            .sum()
            .reset_index()
        )
        df_ca["node"] = "Canada"

        # Calculate the percentage change in demand year-over-year for each commodity
        pc = df_ca.groupby("commodity").apply(
            lambda x: x.sort_values("year").assign(
                pct_change=lambda y: y["value"].pct_change().fillna(0)
            )
        )
        pc = pc.reset_index(drop=True)  # Flatten the DataFrame
        pc = pc[["year", "commodity", "pct_change"]]  # Keep only relevant columns

        # Retrieve historical activity data from the scenario
        hist_act_df = self.scenario.par("historical_activity")

        # Initialize dictionary and lists for storing demands and relevant years
        dmds_dict = {}
        historical_years = hist_act_df["year_act"].unique().tolist()
        demand_years = demand["year"].unique().tolist()
        cmdtys = demand["commodity"].unique().tolist()

        # Extract historical demand data for each commodity and province
        historical_demand = []
        for cmdty in cmdtys:
            for province in ssp_df["iso"].unique():
                for year in demand_years:
                    if year in historical_years:
                        historical_demand.append(
                            demand[
                                (demand["year"] == year)
                                & (demand["commodity"] == cmdty)
                                & (demand["node"] == province)
                            ]
                        )

        # Concatenate all historical demand DataFrames into one
        historical_demand_df = pd.concat(historical_demand, ignore_index=True)

        # Initialize lists for storing final demand data
        ha = historical_demand_df
        dmds = []

        # Iterate through each commodity, province, and year to adjust demand
        for cmdty in cmdtys:
            for province in ssp_df["iso"].unique():
                for year in demand_years:
                    if year in historical_years:
                        # Process historical demands
                        dm = ha.loc[
                            (ha["year"] == year)
                            & (ha["node"] == province)
                            & (ha["commodity"] == cmdty)
                        ]
                        dm = dm[["node", "value"]]

                        # Initialize GDP and GDP per capita lists
                        gdp = [ssp_df.gdp.to_numpy()[0]]
                        gdpc = [ssp_df.gdpc.to_numpy()[0]]

                        # Create DataFrame for historical demand with additional economic indicators
                        dm = pd.DataFrame(
                            {
                                "node": dm.node.to_numpy(),
                                "commodity": cmdty,
                                "level": "useful",
                                "year": year,
                                "time": "year",
                                "value": dm.value.to_numpy(),
                                "unit": "GWa",
                                "ei": dm.value.to_numpy() / gdp,
                                "gdp": gdp,
                                "gdpc": gdpc,
                                "year": year,
                            }
                        )
                        dmds.append(dm)

                        # Update variables for the next iteration
                        dt = dm.value
                        dm0 = dm

                    else:
                        # Calculate future demand based on percentage change
                        pct_change = pc.loc[
                            (pc["year"] == year) & (pc["commodity"] == cmdty),
                            "pct_change",
                        ].values[0]
                        dt = dm.value * (1 + pct_change)

                        dm0 = dm
                        gdpf = []
                        gdpcf = []

                        # Retrieve future GDP and GDP per capita
                        inds = ssp_df["year"] == year
                        gdpf.append(ssp_df.loc[inds, "gdp"].to_numpy()[0])
                        gdpcf.append(ssp_df.loc[inds, "gdpc"].to_numpy()[0])

                        # Unload some variables and call LP downscaling algorithm
                        names = dm0.node.to_numpy()
                        vl = dm0.value.to_numpy()
                        gdpco = dm0.gdpc.to_numpy()

                        # Avoid 0 intensities in future time steps for non-biomass technologies
                        if "biomass" not in cmdty:
                            ei = vl / gdpco
                            vl = ei * gdpco

                        # Simplifying parameters for LP solver
                        beta = gdpco * vl / gdpco
                        phi = gdpcf / gdpco - 1

                        # Define LP objective function coefficients
                        cobj = [1] + [0] * len(names)
                        cobj = np.array(cobj)

                        # Define inequality constraints for LP solver
                        a = np.array([-1] * len(names)).reshape((len(names), 1))
                        b = np.identity(len(names))

                        Aub1 = np.concatenate((a, b), axis=1)
                        bub1 = phi.reshape((len(names), 1))

                        Aub2 = np.concatenate((a, -b), axis=1)
                        bub2 = (-1 * phi).reshape((len(names), 1))

                        Aub3 = np.array([-1] + [0] * len(names)).reshape(
                            (1, len(names) + 1)
                        )
                        bub3 = np.array([[0]])

                        Aub = np.concatenate((Aub1, Aub2, Aub3), axis=0)
                        bub = np.concatenate((bub1, bub2, bub3), axis=0)

                        # Define equality constraints for LP solver
                        Aeq = np.append([0], beta).reshape((1, len(names) + 1))
                        beq = np.array([[dt - sum(beta)]]).reshape((1, 1))

                        # Call LP solver to minimize the maximum difference in growth rates
                        res = linprog(
                            c=cobj,
                            A_ub=Aub,
                            b_ub=bub,
                            A_eq=Aeq,
                            b_eq=beq,
                            bounds=(-np.inf, np.inf),
                            options={"disp": False, "tol": 3.6e-10},
                        )

                        # Calculate the updated demand values based on the LP results
                        val = [
                            (gdpcf[i] * (vl[i] / gdpco[i]) * (1 + res.x[i + 1]))
                            for i in range(len(names))
                        ]

                        # Create DataFrame for future demand with updated values
                        dmf = pd.DataFrame({"node": names, "value": val})

                        dm = pd.DataFrame(
                            {
                                "node": dmf.node.to_numpy(),
                                "commodity": cmdty,
                                "level": "useful",
                                "year": year,
                                "time": "year",
                                "value": dmf.value.to_numpy(),
                                "unit": "GWa",
                                "ei": dmf.value.to_numpy() / gdpf,
                                "gdp": gdpf,
                                "gdpc": gdpcf,
                                "commodity": cmdty,
                                "year": year,
                            }
                        )

                        # Append updated demand to the list
                        dmds.append(dm)

        # Concatenate all demand DataFrames into a single DataFrame
        dmds = pd.concat(dmds, ignore_index=True)

        # Drop unnecessary columns before updating the scenario
        dmds.drop(columns=["ei", "gdp", "gdpc"], inplace=True)

        # Update the scenario with the new demand data
        self.scenario.check_out()
        df = self.scenario.par("demand")
        self.scenario.remove_par("demand", df)
        self.scenario.add_par("demand", dmds)

        # Commit the changes to the scenario
        self.scenario.commit("Updated demands")

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
        # Rename columns in the population DataFrame to match the expected format in the scenario
        population_data.rename(
            columns={"Population": "value", "Province": "node_loc", "Year": "year_act"},
            inplace=True,
        )
        population_data["technology"] = "Population"  # Add a column for technology type
        population_data["mode"] = "P"  # Add a column for mode
        population_data["time"] = "year"  # Add a column for time
        population_data["unit"] = "GWa/a"  # Add a column for unit

        # Rename columns in the GDP DataFrame to match the expected format in the scenario
        gdp_data.rename(
            columns={"GDP": "value", "Province": "node_loc", "Year": "year_act"},
            inplace=True,
        )
        gdp_data["technology"] = "GDP"  # Add a column for technology type
        gdp_data["mode"] = "P"  # Add a column for mode
        gdp_data["time"] = "year"  # Add a column for time
        gdp_data["unit"] = "GWa/a"  # Add a column for unit

        # Concatenate the processed population and GDP data into a single DataFrame
        concatenated_df_socio = pd.concat([population_data, gdp_data])

        # Retrieve the current 'bound_activity_lo' parameter from the scenario
        df = self.scenario.par("bound_activity_lo")

        # Filter out any existing 'Population' and 'GDP' technologies to avoid duplication
        df_filtered = df[~df["technology"].isin(["Population", "GDP"])]

        # Combine the filtered existing data with the new population and GDP data
        df_bound_new = pd.concat([df_filtered, concatenated_df_socio])

        # Update the scenario with the new bounds
        self.scenario.check_out()
        self.scenario.add_par("bound_activity_lo", df_bound_new)
        self.scenario.commit(
            "Added population and GDP bounds"
        )  # Commit the changes with a descriptive message

    def update_historical_activity(self, path: Union[str, Path]):
        """
        Update the historical activity parameter in the scenario with data from a specified path.

        Args:
                        path (str or Path): Path to the historical activity data.
        """
        # Checkout scenario for editing
        self.scenario.check_out()

        # Retrieve the current historical activity data from the scenario
        ha = self.scenario.par("historical_activity")

        # Read new historical activity data from the specified path
        ha_new = pd.read_csv(Path(f"{path}/historical_activity.csv"))

        # Balance import and export values in the new historical activity data
        ha_new = self.balance_import_export(ha_new)

        # Remove the previous historical activity data from the scenario
        self.scenario.remove_par("historical_activity", ha)

        # Add the new, balanced historical activity data to the scenario
        self.scenario.add_par("historical_activity", ha_new)

        # Commit the changes to the scenario with a descriptive message
        self.scenario.commit("Updated historical activity based on new data")

        # Adjust demands in the scenario based on the updated historical activity
        self.adjust_demands()

    def balance_import_export(self, historical_activity: pd.DataFrame):
        """
        Balance energy production, import, and export for each province and year.

        Args:
                        historical_activity (pd.DataFrame): DataFrame containing historical activity data for each province and year.

        Returns:
                        pd.DataFrame: DataFrame with balanced import and export values.
        """
        # Define the provinces involved in the analysis
        PROVINCES = [
            "Alberta",
            "BritishColumbia",
            "Manitoba",
            "Ontario",
            "NewBrunswick",
            "NewfoundlandandLabrador",
            "NovaScotia",
            "PrinceEdwardIsland",
            "Quebec",
            "Saskatchewan",
            "Yukon",
        ]

        # Define the technologies associated with each energy type
        foil_techs = [
            "foil_fs",
            "foil_i",
            "foil_ppl",
            "foil_rc",
            "foil_t_d",
            "foil_trp",
        ]
        loil_techs = [
            "loil_fs",
            "loil_i",
            "loil_ppl",
            "loil_rc",
            "loil_t_d",
            "loil_trp",
        ]
        gas_techs = [
            "gas_cc",
            "gas_ct",
            "gas_fs",
            "gas_i",
            "gas_ppl",
            "gas_rc",
            "gas_t_d",
            "gas_trp",
        ]
        coal_techs = [
            "coal_fs",
            "coal_i",
            "coal_ppl",
            "coal_rc",
            "coal_t_d",
            "coal_trp",
        ]

        def sum_demand(df: pd.DataFrame, techs: list):
            """
            Sum the demand for a given set of technologies within the DataFrame.

            Args:
                            df (pd.DataFrame): DataFrame containing historical activity data.
                            techs (list): List of technology names to sum demand for.

            Returns:
                            pd.Series: Series with the summed demand for each province and year.
            """
            return (
                df[df["technology"].isin(techs)]
                .groupby(["year_act", "node_loc"])["value"]
                .sum()
            )

        def balance_energy(
            row: pd.Series, prod_col: str, imp_col: str, exp_col: str, demand_col: str
        ):
            """
            Balance the energy production, import, and export for a specific energy type.

            Args:
                            row (pd.Series): Row of data containing production, import, export, and demand values.
                            prod_col (str): Column name for production data.
                            imp_col (str): Column name for import data.
                            exp_col (str): Column name for export data.
                            demand_col (str): Column name for demand data.

            Returns:
                            pd.Series: Updated row with balanced production, import, and export values.
            """
            production = row[prod_col]
            imports = row[imp_col]
            exports = row[exp_col]
            demand = row[demand_col]

            # Calculate the net balance of energy
            net_balance = production + imports - exports

            # Adjust imports or exports to meet the demand
            if net_balance < demand:
                imports += demand - net_balance
            elif net_balance > demand:
                exports += net_balance - demand

            # Ensure imports are not negative
            if imports < 0:
                exports += abs(imports)
                imports = 0

            # Update the row with the balanced values
            row[imp_col] = imports
            row[exp_col] = exports
            return row

        # Get the unique years in the historical activity data
        years = historical_activity["year_act"].unique()

        # Iterate over each year to balance energy production, imports, and exports
        for year in years:
            # Filter data for the current year and relevant provinces
            df_year = historical_activity[
                (historical_activity["year_act"] == year)
                & (historical_activity["node_loc"].isin(PROVINCES))
            ]

            # Calculate the total demand for each energy type
            coal_demand = sum_demand(df_year, coal_techs)
            foil_demand = sum_demand(df_year, foil_techs)
            loil_demand = sum_demand(df_year, loil_techs)
            gas_demand = sum_demand(df_year, gas_techs)
            oil_demand = foil_demand.add(
                loil_demand, fill_value=0
            )  # Combine demands for foil and loil

            # Create a pivot table to summarize the production, import, and export data
            pivot_df = df_year.pivot_table(
                index="node_loc", columns="technology", values="value", aggfunc="sum"
            ).reset_index()

            # Define the required columns for production, import, and export data
            required_columns = [
                "coal_extr_mpen",
                "coal_imp",
                "coal_exp",
                "gas_extr_mpen",
                "gas_imp",
                "gas_exp",
                "oil_extr_mpen",
                "oil_imp",
                "oil_exp",
            ]

            # Ensure all required columns are present in the pivot table
            for tech in required_columns:
                if tech not in pivot_df.columns:
                    pivot_df[tech] = 0

            # Extract the production, import, and export data for the current year and provinces
            production_import_export_data = pivot_df[
                ["node_loc"] + required_columns
            ].fillna(0)

            # Create a DataFrame to hold the demand data for the current year and provinces
            demand_data = pd.DataFrame(
                {
                    "node_loc": coal_demand.index.get_level_values("node_loc"),
                    "coal_demand": coal_demand.values,
                    "gas_demand": gas_demand.values,
                    "oil_demand": oil_demand.values,
                }
            ).fillna(0)

            # Merge the production/import/export data with the demand data
            merged_df = production_import_export_data.merge(
                demand_data, on="node_loc", how="left"
            ).fillna(0)

            # Create a copy of the merged data to apply balancing
            balanced_df = merged_df.copy()

            # Apply the balance_energy function to coal, gas, and oil data
            balanced_df = balanced_df.apply(
                balance_energy,
                axis=1,
                prod_col="coal_extr_mpen",
                imp_col="coal_imp",
                exp_col="coal_exp",
                demand_col="coal_demand",
            )

            balanced_df = balanced_df.apply(
                balance_energy,
                axis=1,
                prod_col="gas_extr_mpen",
                imp_col="gas_imp",
                exp_col="gas_exp",
                demand_col="gas_demand",
            )

            balanced_df = balanced_df.apply(
                balance_energy,
                axis=1,
                prod_col="oil_extr_mpen",
                imp_col="oil_imp",
                exp_col="oil_exp",
                demand_col="oil_demand",
            )

            # Update the historical_activity DataFrame with the balanced import and export data
            for index, row in balanced_df.iterrows():
                historical_activity.loc[
                    (historical_activity["year_act"] == year)
                    & (historical_activity["node_loc"] == row["node_loc"])
                    & (historical_activity["technology"] == "coal_imp"),
                    "value",
                ] = row["coal_imp"]
                historical_activity.loc[
                    (historical_activity["year_act"] == year)
                    & (historical_activity["node_loc"] == row["node_loc"])
                    & (historical_activity["technology"] == "coal_exp"),
                    "value",
                ] = row["coal_exp"]
                historical_activity.loc[
                    (historical_activity["year_act"] == year)
                    & (historical_activity["node_loc"] == row["node_loc"])
                    & (historical_activity["technology"] == "gas_imp"),
                    "value",
                ] = row["gas_imp"]
                historical_activity.loc[
                    (historical_activity["year_act"] == year)
                    & (historical_activity["node_loc"] == row["node_loc"])
                    & (historical_activity["technology"] == "gas_exp"),
                    "value",
                ] = row["gas_exp"]
                historical_activity.loc[
                    (historical_activity["year_act"] == year)
                    & (historical_activity["node_loc"] == row["node_loc"])
                    & (historical_activity["technology"] == "oil_imp"),
                    "value",
                ] = row["oil_imp"]
                historical_activity.loc[
                    (historical_activity["year_act"] == year)
                    & (historical_activity["node_loc"] == row["node_loc"])
                    & (historical_activity["technology"] == "oil_exp"),
                    "value",
                ] = row["oil_exp"]

        # Return the updated historical_activity DataFrame
        return historical_activity

    def generate_report(
        self,
        output_path="MESSAGE_CANADA_provincial_baseline_v1.csv",
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
        rep = message_ix.Reporter.from_scenario(
            self.scenario,
            units={"apply": {"var_cost": "", "inv_cost": "", "fix_cost": ""}},
        )
        report = rep.get("message::default")

        if from_excel:
            report_df = pd.read_csv("MESSAGE_NO_example_default_report.csv")
        else:
            report_df = report.timeseries()
            report_df.reset_index(inplace=True)
            report_df.columns = report_df.columns.astype(str)
            report_df.columns = report_df.columns.str.title()

        years = self.scenario.set("year").tolist()
        years = [str(x) for x in years if x >= min_year and x <= max_year]

        report_df.fillna(0, inplace=True)

        report_df.columns = report_df.columns.astype(str)
        report_df = report_df.drop(
            report_df.columns.to_series()["2020" : str(min_year)], axis=1
        )

        in_flows = report_df[report_df["Variable"].str.startswith("in|")]
        out_flows = report_df[report_df["Variable"].str.startswith("out|")]
        all_flows = pd.concat([out_flows, in_flows])

        report_df["Model"] = "MESSAGEix-Canada"
        report_df["Scenario"] = "Reference"
        report_df["Variable"] = report_df["Variable"].str.replace(
            "emis", "Emissions", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "in|final|", "Final Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "out|final|", "Final Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "in|primary|", "Primary Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "out|primary|", "Primary Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "in|secondary|", "Secondary Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "out|secondary|", "Secondary Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "in|renewable|", "Primary Energy|renewable|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "out|renewable|", "Primary Energy|renewable|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "total om cost|", "Total Costs|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "out|useful|", "Useful Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "in|useful|", "Useful Energy|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "CAP_NEW|new capacity|", "Capacity Addition|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "CAP|capacity|", "Capacity|", regex=False
        )
        report_df["Variable"] = report_df["Variable"].str.replace(
            "inv cost|", "Capital Cost|", regex=False
        )
        report_df["Region"] = report_df["Region"].apply(lambda x: x.split("|")[0])

        pyam_df = pyam.IamDataFrame(report_df)

        variable = pyam_df.variable
        pyam_df.aggregate_region(variable, append=True)
        pyam_df.rename({"region": {"World": "Canada"}}, inplace=True)

        pyam_df.to_csv(output_path)

        print(f"Report saved to {output_path}")

    def clone_scenario(self, scenario_name, keep_solution=False) -> tuple:
        """
        Clone an existing scenario

        """
        config = self.config_file

        modelName = config["general"]["model_name"]
        scenarioName = config["general"]["scenario_name"]
        platform_name = config["general"]["ix_platform"]
        version = config["general"]["version"]
        annotation = config["general"]["annotation"]
        mp = ixmp.Platform(name=platform_name)
        self.scenario = message_ix.Scenario(
            mp, modelName, scenarioName, version=version, annotation=annotation
        )
        scenario1 = self.scenario.clone(
            modelName,
            scenario_name,
            keep_solution=keep_solution,
        )

        return scenario1

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

        """
		config_path = os.path.join(self.scenario_path, "config.toml")# Path(f"../scenarios/{scenario_name}/config.toml")

		if not config_path.exists():
			raise FileNotFoundError(f"Config file does not exist at {config_path}")
		"""

        # Config verification:
        self.config_validation()

        # Scenario set-up
        start = time.time()
        config = self.config_file

        modelName = config["general"]["model_name"]
        scenarioName = config["general"]["scenario_name"]
        platform_name = config["general"]["ix_platform"]
        version = config["general"]["version"]
        annotation = config["general"]["annotation"]
        process_historical = config["pre_process"]["process_historical_data"]
        add_hydrogen_shares_f = config["pre_process"]["add_hydrogen_shares"]
        add_obps_baseline = config["pre_process"]["apply_obps_baseline"]
        add_obps_netzero = config["pre_process"]["apply_obps_netzero"]
        use_reporter = config["post_process"]["generate_reporter_output"]
        solve = config["model"]["solve"]
        to_excel = config["post_process"]["export_to_xlsx"]
        add_techs = config["pre_process"]["add_technology"]["add_techs"]

        # TODO add option for SSP
        # ssp = 'SSP2'

        mp = ixmp.Platform(name=platform_name)
        self.scenario = message_ix.Scenario(
            mp, modelName, scenarioName, version=version, annotation=annotation
        )

        caseName = (
            self.scenario.model
            + "__"
            + self.scenario.scenario
            + "__v"
            + str(self.scenario.version)
        )

        script_dir = Path(__file__).resolve().parent
        scenario_folder = script_dir / config["data"]["scenario_folder"]
        excel_path = script_dir / config["data"]["provincial_input_file"]
        # Update message scenario
        self.scenario.read_excel(
            excel_path, add_units=True, commit_steps=False, init_items=True
        )

        if process_historical:
            self.update_historical_activity(path=scenario_folder)

        if add_hydrogen_shares_f:
            path_to_hydrogen_data = script_dir / scenario_folder
            self.add_hydrogen_shares(path=path_to_hydrogen_data)

        if add_obps_baseline:
            path_to_obps_data = script_dir / scenario_folder
            apply_obps_netzero(
                scenario=scenario_folder, data_file_path=path_to_obps_data
            )

        if add_obps_netzero:
            path_to_obps_data = script_dir / scenario_folder
            apply_obps_baseline(
                scenario=scenario_folder, data_file_path=path_to_obps_data
            )

        if add_techs:
            self.add_technology(techs_file=f"{scenario_folder}/technology.yaml")

        end = time.time()
        print(
            f"\n==================================================\n\
		Model creation time: {round((end - start) / 60)} Min and {round((end - start) % 60)} Sec \
		\n=================================================="
        )

        if solve:
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

            except Exception:
                print(f"Scenario {caseName} did not solve\n")

            if use_reporter:
                self.generate_report(
                    self.scenario,
                    output_path=f"{caseName}.csv",
                    min_year=2020,
                    max_year=2060,
                    from_excel=False,
                    unit_correct=True,
                )

        if to_excel:
            self.scenario.to_excel(f"{caseName}.xlsx")

        return mp, self.scenario, scenario_folder


# Plotter class
class Plotter_MSG:

    def __init__(self, scenario):
        self.scenario = scenario  # MESSAGE scenario object
        self.color_map = {
            "CH4-AFOLU": "darkgreen",
            "CH4-Other": "lime",
            "CO2-AFOLU": "dimgrey",
            "CO2-Other": "lightgrey",
            "F-Gases": "black",
            "N2O-AFOLU": "maroon",
            "N2O-Other": "red",
            "Other": "orange",
            "TCE": "black",
            "biomass": "green",
            "biomass (modern)": "lightgreen",
            "biomass (solids)": "lightgreen",
            "biomass (traditional)": "green",
            "buildings": "green",
            "coal": "black",
            "coal (solids)": "black",
            "crudeoil": "red",
            "district heat": "red",
            "electr": "purple",
            "electricity": "purple",
            "electricity generation": "purple",
            "ethanol": "lightgreen",
            "exports": "blueviolet",
            "fuel oil": "firebrick",
            "fueloil": "firebrick",
            "gas": "aqua",
            "gas_weu": "olive",
            "gases": "aqua",
            "gasification": "aqua",
            "geothermal": "tan",
            "heat": "red",
            "heat pump (gas)": "darkturquoise",
            "heat pump (el)": "turquoise",
            "heavy fuel oil": "firebrick",
            "hydro": "royalblue",
            "hydrogen": "sienna",
            "i_feed": "green",
            "i_spec": "salmon",
            "i_therm": "red",
            "imports": "lightcoral",
            "industry": "darkred",
            "light oil": "salmon",
            "lightoil": "salmon",
            "liquids": "royalblue",
            "LNG": "yellow",
            "methanol": "darkgreen",
            "natural gas (CC)": "aqua",
            "natural gas (ST + CT)": "darkturquoise",
            "non-commercial": "darkgreen",
            "non-energy (feedstock)": "darkblue",
            "nuclear": "yellow",
            "oil": "red",
            "others": "lightgrey",
            "production": "darkblue",
            "production (unconv.)": "skyblue",
            "rc_spec": "darkblue",
            "rc_therm": "firebrick",
            "refinery": "gray",
            "solar": "gold",
            "solar CSP": "coral",
            "solar PV": "gold",
            "transport": "grey",
            "wind": "skyblue",
            "wind offshore": "dodgerblue",
            "wind onshore": "skyblue",
        }

        # Minimum value as % of max value to show in the graph
        self.min_val = 0.02
        self.min_abs = 2  # min abs value to show in the plots
        self.renaming = {
            "biomass_nc": "biomass (traditional)",
            "biomass_rc": "biomass (modern)",
            "coal_rc": "coal",
            "crudeoil": "oil",
            "d_heat": "district heat",
            "elec_rc": "electric heating",
            "elec_trp": "electric transport",
            "electr": "electricity",
            "electr_eur_afr": "electricity",
            "foil_rc": "heavy fuel oil",
            "fueloil": "heavy fuel oil",
            "gas_rc": "gas",
            "heat_rc": "district heat",
            "hp_el_rc": "heat pump (el)",
            "hp_gas_rc": "heat pump (gas)",
            "lh2": "hydrogen",
            "lightoil": "light oil",
            "loil_rc": "light oil",
            "solar_pv": "solar",
            "solar_csp": "solar",
            "solar_rc": "solar",
            "solar_th": "solar",
            "sp_el_I": "electricity",
            "sp_el_RC": "electricity",
            "stor_ppl": "storage_loss",
            "wind_onshore": "wind",
            "wind_offshore": "wind",
        }

        # Order of commodities in the results
        self.crudes = [x for x in set(self.scenario.set("commodity")) if "crude_" in x]
        self.gases = [x for x in set(self.scenario.set("commodity")) if "gas_" in x]
        self.order = (
            ["coal", "caol_rc", "coal_i", "crudeoil"]
            + self.crudes
            + ["fueloil", "foil_rc", "foil_i", "lightoil", "loil_rc", "loil_i"]
            + self.gases
            + [
                "biomass",
                "biomass_nc",
                "biomass_rc",
                "d_heat",
                "elec_rc",
                "electr",
                "ethanol",
                "gas",
                "gas_rc",
                "hp_el_rc",
                "hp_gas_rc",
                "hydro",
                "hydrogen",
                "methanol",
                "nuclear",
                "others",
                "solar_csp",
                "solar_pv",
                "solar_rc",
                "sp_el_I",
                "sp_el_RC",
                "wind_offshore",
                "wind_onshore",
            ]
        )

        # Unit conversion
        self.unitc = 8.76 * 3.6  # Conversion from GWa to PJ
        self.unitname = "(PJ)"

        self.unit_el = 8760 / 1000  # Conversion from GWa to TWh
        self.unitname_el = "(TWh)"

        self.unit_cap = 1000  # Conversion from GW to MW
        self.unitname_cap = "(MW)"

        # Graphing parameters
        self.kind = "bar"
        self.dict_plot = {
            "Oil supply " + self.unitname: self.kind,
            "Oil derivative supply " + self.unitname: self.kind,
            "Oil derivative use " + self.unitname: self.kind,
            "Gas supply " + self.unitname: self.kind,
            "Gas utilization " + self.unitname: self.kind,
            "Coal supply " + self.unitname: self.kind,
            "Coal utilization " + self.unitname: self.kind,
            "Biomass supply " + self.unitname: self.kind,
            "Biomass utilization " + self.unitname: self.kind,
            "Electricity generation " + self.unitname_el: self.kind,
            "Power plant capacity " + self.unitname_cap: self.kind,
            "Power plant new capacity " + self.unitname_cap: self.kind,
            "Electricity use " + self.unitname_el: self.kind,
            "Primary energy supply " + self.unitname: self.kind,
            "Final energy consumption " + self.unitname: self.kind,
            "Energy use: Transport " + self.unitname: self.kind,
            "Energy use: Industry " + self.unitname: self.kind,
            "Energy use: Buildings " + self.unitname: self.kind,
            "Non-energy use: Feedstock " + self.unitname: self.kind,
            "Useful energy " + self.unitname: self.kind,
            "Energy exports " + self.unitname: self.kind,
            "Energy imports " + self.unitname: self.kind,
            "Total GHG emissions (MtCeq)": self.kind,
        }

        self.abbrev_prov = {
            "Alberta": "AB",
            "BritishColumbia": "BC",
            "Saskatchewan": "SK",
            "Manitoba": "MB",
            "Ontario": "ON",
            "Quebec": "QC",
            "NewBrunswick": "NB",
            "NewfoundlandandLabrador": "NL",
            "PrinceEdwardIsland": "PE",
            "NovaScotia": "NS",
            "Yukon": "YT",
            "NorthwestTerritories": "NT",
            "Nunavut": "NU",
        }

        self.fntsz = 5  # Font size
        self.fntcol = "dimgray"  # Font color
        self.lw = 0.1  # Line width
        self.ticksz = -1  # Tick size
        self.tickwdt = 0.2  # Tick width

    # Modules and functions for creating the plotting dataframes
    def group(self, df, groupby, result, limit, lyr) -> pd.DataFrame:
        """The function groups dataframe df over an index and column."""
        df = df.groupby(groupby, as_index=False).sum()
        df = pd.pivot_table(
            df, index=groupby[0], columns=groupby[1], values=result, fill_value=0
        )
        return df

    def multiply_df(self, df1, column1, df2, column2) -> pd.DataFrame:
        """The function merges dataframe df1 with df2 and multiplies column1 with
        column2. The function returns the new merged dataframe with the result
        of the muliplication in the column 'product'.
        """
        index = [
            x
            for x in ["mode", "node_loc", "technology", "time", "year_act", "year_vtg"]
            if x in df1.columns
        ]
        df = df1.merge(df2, how="outer", on=index)
        df["product"] = df.loc[:, column1] * df.loc[:, column2]
        return df

    def attach_history(self, tec, plotyrs):
        """This function calculates historical data to be attached to the model
        results
        """
        parname = "historical_activity"
        act_hist = self.scenario.par(parname, {"technology": tec, "year_act": plotyrs})
        act_hist = act_hist[["technology", "year_act", "value"]]
        act_hist = pd.pivot_table(
            act_hist, index="year_act", columns="technology"
        ).fillna(0)
        act_hist = act_hist[act_hist.columns[(act_hist > 0).any()]]
        act_hist.columns = act_hist.columns.droplevel(0)
        return act_hist

    def plotdf(self, tec, com, direction, plotyrs, yr):
        """The main function for calculating output and attaching historical data"""
        # Reading input or output coefficients based on the direction
        inputs = self.scenario.par(direction)
        inputs = inputs.loc[inputs.year_act.isin(plotyrs)]
        inputs = inputs.loc[
            (inputs.technology.isin(tec)) & (inputs.commodity.isin(com))
        ][["technology", "year_act", "value"]]
        inputs = inputs.groupby(["technology", "year_act"], as_index=False).mean()
        inputs = inputs.pivot(index="year_act", columns="technology")
        inputs = inputs[inputs.columns[(inputs != 0).any()]]
        inputs.columns = inputs.columns.droplevel(0)

        # Reading output variable of activity
        act = self.scenario.var("ACT").loc[
            self.scenario.var("ACT").year_act.isin(plotyrs)
        ]
        activity = act.loc[act.technology.isin(tec)][["technology", "year_act", "lvl"]]

        activity = activity.groupby(["technology", "year_act"], as_index=False).sum()
        activity = activity.pivot(index="year_act", columns="technology").fillna(0)
        activity = activity[activity.columns[(activity != 0).any()]]
        activity.columns = activity.columns.droplevel(0)

        # Addding Historical Activity (to the graphs)
        act_hist = self.attach_history(tec, plotyrs)
        activity_tot = activity.add(act_hist, fill_value=0)

        df_plot = inputs * activity_tot
        df_plot = df_plot.fillna(0)
        df_plot = df_plot[df_plot.columns[(df_plot > 0).any()]]
        return df_plot

    def plotdf_com(self, tec, com, direction, plotyrs, yr):
        """This funcion aggregates commodities for reporting at each level"""

        df_plot_com = df_plot_el = pd.DataFrame(index=plotyrs)
        for commodities in com:

            inputs = self.scenario.par(direction)
            inputs = inputs.loc[inputs.year_act.isin(plotyrs)]
            inputs = inputs.loc[
                (inputs.technology.isin(tec)) & (inputs.commodity == commodities)
            ][["technology", "year_act", "value"]]
            inputs = inputs.groupby(["technology", "year_act"], as_index=False).mean()
            inputs = inputs.pivot(index="year_act", columns="technology")
            inputs = inputs[inputs.columns[(inputs != 0).any()]]
            inputs.columns = inputs.columns.droplevel(0)
            act = self.scenario.var("ACT").loc[
                self.scenario.var("ACT").year_act.isin(plotyrs)
            ]
            activity = act.loc[act.technology.isin(tec)][
                ["technology", "year_act", "lvl"]
            ]

            activity = activity.groupby(
                ["technology", "year_act"], as_index=False
            ).sum()
            activity = activity.pivot(index="year_act", columns="technology")
            activity = activity[activity.columns[(activity != 0).any()]]
            activity.columns = activity.columns.droplevel(0)

            # Attaching history
            act_hist = self.attach_history(tec, plotyrs)
            activity = activity.add(act_hist, fill_value=0)

            df_plot = inputs * activity
            df_plot = df_plot.fillna(0)
            df_plot = df_plot.loc[:, (df_plot != 0).any(axis=0)]

            cols_hydro = [col for col in df_plot.columns if "hydro" in col]
            cols_wind = [col for col in df_plot.columns if "wind" in col]
            cols_solar = [col for col in df_plot.columns if "solar" in col]
            cols_others = [
                x
                for x in df_plot.columns
                if x not in (cols_hydro + cols_wind + cols_solar)
            ]
            dict_ele = {
                "cols_hydro": (cols_hydro, "hydro"),
                "cols_wind": (cols_wind, "wind"),
                "cols_solar": (cols_solar, "solar"),
                "cols_others": (cols_others, "electr"),
            }

            if commodities == "electr":
                for tecs in list(dict_ele.keys()):
                    df_plot_el[dict_ele["{}".format(tecs)][1]] = (
                        df_plot.filter(items=dict_ele["{}".format(tecs)][0])
                        .sum(axis=1)
                        .to_frame()
                    )
            else:
                df_plot = df_plot.sum(axis=1).to_frame()
                df_plot[commodities] = df_plot
                df_plot_com = df_plot_com.join(df_plot[commodities])
        df_plot_com = df_plot_com.join(df_plot_el)

        return df_plot_com

    # Aggregating sectors
    def mappings(self, plotyrs, df, groupby="sector"):
        df_sec = pd.DataFrame(index=plotyrs)

        if groupby == "sector":
            cols_ind = [col for col in df.columns if "_i" in col] + [
                col for col in df.columns if "_I" in col
            ]
            cols_ind = [
                x
                for x in cols_ind
                if not any(y in x for y in ["eth_ic", "meth_ic", "bio_is", "_imp"])
            ]
            cols_trp = [col for col in df.columns if "_trp" in col]
            cols_rc = [
                col for col in df.columns if any(y in col for y in ["_rc", "_RC"])
            ]
            cols_nc = [col for col in df.columns if "_nc" in col]
            cols_ene = [col for col in df.columns if "_fs" in col]
            cols_exp = [col for col in df.columns if "_exp" in col]
            cols_imp = [col for col in df.columns if "_imp" in col]
            cols_ppl = [
                col
                for col in df.columns
                if any(
                    y in col
                    for y in [
                        "_ppl",
                        "_adv",
                        "bio_istig",
                        "gas_cc",
                        "gas_cc_ccs",
                        "gas_ct",
                        "igcc",
                        "igcc_ccs",
                        "loil_cc",
                    ]
                )
            ]
            cols_eth = [
                col
                for col in df.columns
                if any(y in col for y in ["eth_bio", "liq_bio"])
            ]
            cols_meth = [
                col
                for col in df.columns
                if any(y in col for y in ["meth_ng", "meth_coal"])
            ]
            cols_loil = [
                col for col in df.columns if any(y in col for y in ["syn_liq"])
            ]
            cols_gas = [
                col
                for col in df.columns
                if any(y in col for y in ["coal_gas", "gas_bio"])
            ]
            cols_hyd = [col for col in df.columns if any(y in col for y in ["h2_"])]

            cols_prod = [
                col
                for col in df.columns
                if any(
                    y in col
                    for y in [
                        "_extr",
                        "_extr_1",
                        "_extr_2",
                        "_extr_3",
                        "_extr_4",
                        "extr_ch4",
                    ]
                )
            ]

            cols_prod2 = [
                col
                for col in df.columns
                if any(y in col for y in ["_extr_5", "_extr_6", "_extr_7", "_extr_8"])
            ]

            cols_ref = [
                col for col in df.columns if any(y in col for y in ["ref_h", "ref_l"])
            ]

            dict_sectors = {
                "production": cols_prod,
                "production (unconv.)": cols_prod2,
                "refinery": cols_ref,
                "industry": cols_ind,
                "transport": cols_trp,
                "non-energy (feedstock)": cols_ene,
                "buildings": cols_rc,
                "non-commercial": cols_nc,
                "electricity generation": cols_ppl,
                "exports": cols_exp,
                "imports": cols_imp,
                "ethanol": cols_eth,
                "methanol": cols_meth,
                "light oil": cols_loil,
                "gasification": cols_gas,
                "hydrogen": cols_hyd,
                "production": cols_prod,
                "production (unconv.)": cols_prod2,
                "refinery": cols_ref,
            }
        else:
            cols_solar = [
                col
                for col in df.columns
                if any(y in col for y in ["solar_pv", "solar_res"])
            ]
            cols_csp = [
                col
                for col in df.columns
                if any(y in col for y in ["csp_sm", "solar_th_ppl"])
            ]
            cols_wind = [
                col
                for col in df.columns
                if any(y in col for y in ["wind_ppl", "wind_res"])
            ]
            cols_windoff = [
                col
                for col in df.columns
                if any(y in col for y in ["wind_ppf", "wind_ref"])
            ]
            cols_coal = [
                col
                for col in df.columns
                if any(y in col for y in ["coal_ppl", "coal_adv", "syn_liq", "igcc"])
            ]
            cols_gas1 = [
                col
                for col in df.columns
                if any(y in col for y in ["gas_ppl", "gas_ct"])
            ]
            cols_gas2 = [col for col in df.columns if any(y in col for y in ["gas_cc"])]
            cols_loil = [
                col
                for col in df.columns
                if any(y in col for y in ["loil_ppl", "loil_cc"])
            ]
            cols_foil = [
                col
                for col in df.columns
                if any(y in col for y in ["foil_ppl", "foil_cc"]) or col == "oil_ppl"
            ]
            cols_nuc = [
                col for col in df.columns if any(y in col for y in ["nuc_hc", "nuc_lc"])
            ]
            cols_hyd = [
                col
                for col in df.columns
                if any(y in col for y in ["hydro_lc", "hydro_hc"])
            ]
            cols_bio = [
                col
                for col in df.columns
                if any(y in col for y in ["bio_ppl", "bio_istig"])
            ]
            cols_geo = [col for col in df.columns if any(y in col for y in ["geo_ppl"])]
            dict_sectors = {
                "coal": cols_coal,
                "heavy fuel oil": cols_foil,
                "light oil": cols_loil,
                "natural gas (ST + CT)": cols_gas1,
                "natural gas (CC)": cols_gas2,
                "nuclear": cols_nuc,
                "hydro": cols_hyd,
                "biomass": cols_bio,
                "wind onshore": cols_wind,
                "wind offshore": cols_windoff,
                "solar PV": cols_solar,
                "solar CSP": cols_csp,
                "geothermal": cols_geo,
            }

        # Adding everything else to others
        cols_others = [
            x
            for x in df.columns
            if x not in list(itertools.chain.from_iterable(dict_sectors.values()))
        ]
        dict_sectors.update({"others": cols_others})

        # Mapping the entries (columns) to lables
        for label, tecs in dict_sectors.items():
            df[label] = df.filter(items=tecs).sum(axis=1).to_frame()
            df_sec = df_sec.join(df[label])

        return df_sec.fillna(0)

    # Aggregating results for industry and energy sectors
    def plotdf_ind(self, tec, com, direction, plotyrs, yr):
        df_plot_ind = pd.DataFrame(index=plotyrs)

        inputs = self.scenario.par(direction)
        inputs = inputs.loc[inputs.year_act.isin(plotyrs)]
        inputs = inputs.loc[
            (inputs.technology.isin(tec)) & (inputs.commodity.isin(com))
        ][["technology", "year_act", "value"]]
        inputs = inputs.groupby(["technology", "year_act"], as_index=False).mean()
        inputs = inputs.pivot(index="year_act", columns="technology")
        inputs = inputs[inputs.columns[(inputs != 0).any()]]
        inputs.columns = inputs.columns.droplevel(0)
        act = self.scenario.var("ACT").loc[
            self.scenario.var("ACT").year_act.isin(plotyrs)
        ]
        activity = act.loc[act.technology.isin(tec)][["technology", "year_act", "lvl"]]

        activity = activity.groupby(["technology", "year_act"], as_index=False).sum()
        activity = activity.pivot(index="year_act", columns="technology")
        activity = activity[activity.columns[(activity != 0).any()]]
        activity.columns = activity.columns.droplevel(0)

        # Attaching history
        act_hist = self.attach_history(tec, plotyrs)
        activity = activity.add(act_hist, fill_value=0)

        df_plot = inputs * activity
        df_plot = df_plot.fillna(0)
        df_plot = df_plot.loc[:, (df_plot != 0).any(axis=0)]

        fuel = {
            "biomass": ["biomass_i"],
            "coal": ["coal_i"],
            "foil": ["foil_fs", "foil_i"],
            "electr": ["elec_i", "sp_el_I", "sp_liq_I"],
            "gas": ["gas_fs", "gas_i"],
            "d_heat": ["heat_i"],
            "loil": ["loil_fs", "loil_i"],
            "solar": ["solar_i"],
        }

        for source in list(fuel.keys()):
            df_plot["{}".format(source)] = (
                df_plot.filter(items=fuel["{}".format(source)]).sum(axis=1).to_frame()
            )
            df_plot_ind = df_plot_ind.join(df_plot["{}".format(source)])

        others = df_plot_ind.loc[
            :, (df_plot_ind.ix[yr] <= df_plot_ind.ix[yr].sum() * 0.01)
        ].sum(axis=1)
        df_plot_ind = df_plot_ind.loc[
            :, (df_plot_ind.ix[yr] > df_plot_ind.ix[yr].sum() * 0.01)
        ]
        df_plot_ind["others"] = others

        return df_plot_ind

    # A function for adding history
    def add_history(self, tecs, nodeloc, df2, groupby):
        df1_hist = self.scenario.par(
            "historical_activity", {"technology": tecs, "node_loc": nodeloc}
        ).rename({"value": "lvl"}, axis=1)
        df2_hist = (
            df2.groupby(
                ["year_act", "technology", "mode", "node_loc", "commodity", "time"],
                as_index=False,
            )
            .mean(numeric_only=True)
            .drop(["year_vtg"], axis=1)
        )
        df_hist = self.multiply_df(df1_hist, "lvl", df2_hist, "value")
        df_hist = self.group(df_hist, ["year_act", groupby], "product", 0.0, None)
        return df_hist

    # A function for making model output in a compact way
    def model_output(self, tecs, nodeloc, parname, coms=None):
        df1 = self.scenario.var("ACT", {"technology": tecs, "node_loc": nodeloc})
        df2 = self.scenario.par(parname, {"technology": tecs, "node_loc": nodeloc})
        if coms:
            if isinstance(coms, str):
                coms = [coms]
            df2 = df2.loc[df2["commodity"].isin(coms)]
        df = self.multiply_df(df1, "lvl", df2, "value")
        return df, df2

    # A function for reordering the columns of a dataframe and leaving the rest
    def com_order(self, df, order):
        order = [x for x in order if x in df.columns]
        new_order = order + [x for x in set(df.columns) if x not in order]
        df = df.reindex(new_order, axis=1)
        return df

    # The main plotting function
    def plotter(
        self, case, nodeloc, path, yr_min, yr_max, plots="all", not_plots=[]
    ) -> pd.DataFrame:

        # 1) Initialization and importing required data
        cwd = os.getcwd()
        os.chdir(path)

        # Checking if the scenario has a solution
        if not self.scenario.has_solution():
            raise ("Submitted scenario has no solution to plot!")

        if not self.scenario.set("cat_year", {"type_year": "lastmodelyear"}).empty:
            last_yr = self.scenario.set("cat_year", {"type_year": "lastmodelyear"})[
                "year"
            ].item()
        else:
            last_yr = max(self.scenario.set("year"))

        plotyrs = [
            int(i) for i in list(self.scenario.set("year")) if int(i) < int(last_yr)
        ]
        yr = self.scenario.set("cat_year", {"type_year": "firstmodelyear"}).year.item()

        # 2) Reading and sorting solution data
        # A dictionary for saving all the results for plotting
        alldf = {}

        # 2.1) Power plant activity and capacity
        cap = self.scenario.var("CAP", {"year_vtg": plotyrs})
        cap_new = self.scenario.var("CAP_NEW", {"year_vtg": plotyrs})
        cap_hist = self.scenario.par("historical_new_capacity", {"year_vtg": plotyrs})

        tec = self.scenario.par(
            "output", {"commodity": "electr", "level": "secondary"}
        )["technology"]

        tec = tec.tolist() + ["stor_ppl"]
        # Power plant capacity
        ppl_cap = cap.loc[cap.technology.isin(tec)][["technology", "year_act", "lvl"]]
        ppl_cap = ppl_cap.groupby(["technology", "year_act"], as_index=False).sum()
        ppl_cap = ppl_cap.pivot(index="year_act", columns="technology")
        ppl_cap = ppl_cap[ppl_cap.columns[(ppl_cap != 0).any()]]
        ppl_cap.columns = ppl_cap.columns.droplevel(0)
        ppl_cap = ppl_cap.loc[:, (ppl_cap > 0).any()]

        # Power plant new capacity
        ppl_cap_new = cap_new.loc[(cap_new.technology.isin(tec)) & (cap_new.lvl > 0)][
            ["technology", "year_vtg", "lvl"]
        ]
        ppl_cap_new = pd.pivot_table(
            ppl_cap_new, index="year_vtg", columns="technology"
        ).fillna(0)
        ppl_cap_new.columns = ppl_cap_new.columns.droplevel(0)

        # Power plant historical capacity
        ppl_cap_hist = cap_hist.loc[
            (cap_hist.technology.isin(tec)) & (cap_hist.value > 0)
        ][["technology", "year_vtg", "value"]]
        ppl_cap_hist = pd.pivot_table(
            ppl_cap_hist, index="year_vtg", columns="technology"
        ).fillna(0)
        ppl_cap_hist.columns = ppl_cap_hist.columns.droplevel(0)

        cap_new_tot = (ppl_cap_new.add(ppl_cap_hist, fill_value=0)).fillna(0)
        cap_new_tot = cap_new_tot[cap_new_tot.columns[(cap_new_tot > 0.001).any()]]

        # Power plant activity
        elec = self.plotdf(tec, ["electr"], "output", plotyrs, yr)

        # Treatment of storage losses
        if "stor_ppl" in elec.columns:
            d_stor = self.scenario.par("input", {"technology": "stor_ppl"})
            d_stor = d_stor.loc[d_stor["year_act"].isin(plotyrs)][
                ["technology", "year_act", "value"]
            ]
            d_stor = d_stor.groupby(["year_act"]).mean()
            elec["stor_ppl"] *= -d_stor["value"]
            elec.rename(self.renaming, axis=1, inplace=True)

        elec = self.mappings(plotyrs, elec, groupby="technology")
        ppl_cap = self.mappings(plotyrs, ppl_cap, groupby="technology")
        cap_new_tot = self.mappings(plotyrs, cap_new_tot, groupby="technology")

        alldf["Electricity generation " + self.unitname_el] = elec * self.unit_el
        alldf["Power plant capacity " + self.unitname_cap] = ppl_cap * self.unit_cap
        alldf["Power plant new capacity " + self.unitname_cap] = (
            cap_new_tot * self.unit_cap
        )

        # 2.2) Electricity usage
        tecs = list(
            set(
                self.scenario.par(
                    "input", {"commodity": "electr", "level": "final"}
                ).technology
            )
        )
        tecs = tecs + ["stor_ppl"]

        for current_node in nodeloc:
            # Prepration for Excel writings
            writer_xls = pd.ExcelWriter(
                path + "\\" + case + f"_{current_node}" + ".xlsx", engine="xlsxwriter"
            )
            df, df2 = self.model_output(tecs, current_node, "input", "electr")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)

            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (
                (df_hist + df)
                .fillna(0)
                .rename(
                    {
                        "sp_el_RC": "buildings",
                        "sp_el_I": "industry",
                        "elec_trp": "transport",
                    },
                    axis=1,
                )
            )
            alldf["Electricity use " + self.unitname_el] = df * self.unit_el

            # 2.3) Natural Gas supply (incl. import) and usage
            gas_tecs = ["gas_t_d", "gas_t_d_ch4", "gas_bal"]
            tecs = list(
                set(self.scenario.par("output", {"commodity": "gas"}).technology)
                - set(gas_tecs)
            )
            df, df2 = self.model_output(tecs, current_node, "output", "gas")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df_hist + df).fillna(0)
            alldf["Gas supply " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # Natural gas usage
            gas_tecs = ["gas_t_d", "gas_t_d_ch4", "gas_bal"]
            tecs = list(
                set(self.scenario.par("input", {"commodity": "gas"}).technology)
                - set(gas_tecs)
            )
            df, df2 = self.model_output(tecs, current_node, "input", "gas")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df_hist + df).fillna(0)
            alldf["Gas utilization " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # 2.4) Coal supply and utilization
            coal_tecs = ["coal_t_d", "coal_bal", "coal_exp"]
            tecs = list(
                set(self.scenario.par("output", {"commodity": "coal"}).technology)
                - set(coal_tecs)
            )
            df, df2 = self.model_output(tecs, current_node, "output", "coal")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Coal supply " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # Coal utilization
            coal_tecs = ["coal_t_d", "coal_bal", "coal_extr", "coal_extr_ch4"]
            tecs = list(
                set(self.scenario.par("input", {"commodity": "coal"}).technology)
                - set(coal_tecs)
            )
            df, df2 = self.model_output(tecs, current_node, "input", "coal")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Coal utilization " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # 2.5) Oil derivatives supply and use
            tecs = list(
                set(
                    self.scenario.par(
                        "output",
                        {"commodity": ["fueloil", "lightoil"], "level": ["secondary"]},
                    ).technology
                )
            )

            df, df2 = self.model_output(
                tecs, current_node, "output", ["fueloil", "lightoil"]
            )
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Oil derivative supply " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # Oil derivatives utilisation
            tecs = list(
                set(
                    self.scenario.par(
                        "input", {"commodity": ["fueloil", "lightoil"]}
                    ).technology
                )
                - set(["loil_t_d", "foil_t_d"])
            )
            df, df2 = self.model_output(
                tecs, current_node, "input", ["fueloil", "lightoil"]
            )
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Oil derivative use " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # 2.6) Oil supply
            tecs = list(
                set(self.scenario.par("output", {"commodity": ["crudeoil"]}).technology)
                - set(["oil_bal", "oil_exp"])
            )
            df, df2 = self.model_output(tecs, current_node, "output", "crudeoil")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Oil supply " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # 2.7) Biomass provision
            tecs = list(
                set(
                    self.scenario.par(
                        "output", {"commodity": ["biomass"], "level": ["primary"]}
                    ).technology
                )
            )
            df, df2 = self.model_output(tecs, current_node, "output")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Biomass supply " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # Biomass utilisation
            tecs = list(
                set(
                    self.scenario.par(
                        "input",
                        {"commodity": ["biomass"], "level": ["primary", "final"]},
                    ).technology
                )
                - set(["biomass_t_d"])
            )
            df, df2 = self.model_output(tecs, current_node, "input", "biomass")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = (df + df_hist).fillna(0)
            alldf["Biomass utilization " + self.unitname] = (
                self.mappings(plotyrs, df) * self.unitc
            )

            # 3) Sector related results
            # 3.1) Transport
            tecs = list(
                set(
                    self.scenario.par("output", {"commodity": ["transport"]}).technology
                )
            )
            df, df2 = self.model_output(tecs, current_node, "input")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Energy use: Transport " + self.unitname] = df * self.unitc

            # 3.2) Industry
            tecs = list(
                set(
                    self.scenario.par(
                        "output", {"commodity": ["i_spec", "i_therm"]}
                    ).technology
                )
            )
            df, df2 = self.model_output(tecs, current_node, "input")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Energy use: Industry " + self.unitname] = df * self.unitc

            # 3.3) Non-energy (feedstock) use in Industry
            tecs = list(
                set(self.scenario.par("output", {"commodity": ["i_feed"]}).technology)
            )
            df, df2 = self.model_output(tecs, current_node, "input")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)

            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Non-energy use: Feedstock " + self.unitname] = df * self.unitc

            # 3.4) Residencial and commercial
            tecs = list(
                set(
                    self.scenario.par(
                        "output", {"commodity": ["rc_spec", "rc_therm", "non-comm"]}
                    ).technology
                )
            )
            df, df2 = self.model_output(tecs, current_node, "input")
            df = self.group(df, ["year_act", "technology"], "product", 0.0, yr)

            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "technology")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Energy use: Buildings " + self.unitname] = df * self.unitc

            # 4) Energy balances
            # 4.1) Primary energy : production + imports - exports
            tecs = list(
                set(self.scenario.par("output", {"level": ["primary"]}).technology)
            )
            df, df2 = self.model_output(tecs, current_node, "output")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)

            # Renewables
            tecs = list(
                set(self.scenario.par("input", {"level": ["renewable"]}).technology)
            )
            df_re, df2 = self.model_output(tecs, current_node, "input")
            df_re = self.group(df_re, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "commodity")
            df = df.add(
                self.com_order((df_hist + df_re).fillna(0), self.order), fill_value=0
            )

            # Import technologies
            tecs_imp = [
                x for x in set(self.scenario.set("technology")) if x.endswith("_imp")
            ]
            df_imp, df2_imp = self.model_output(tecs_imp, current_node, "output")
            df_imp = self.group(df_imp, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs_imp, current_node, df2_imp, "commodity")
            df_imp = self.com_order((df_hist + df_imp).fillna(0), self.order)
            if not df_imp.empty:
                df = df.add(df_imp, fill_value=0)

                # Export technologies
            tecs_exp = [x for x in list(self.scenario.set("technology")) if "_exp" in x]
            df_exp, df2_exp = self.model_output(tecs_exp, current_node, "output")
            df_exp = self.group(df_exp, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs_exp, current_node, df2_exp, "commodity")
            df_exp = self.com_order((df_hist + df_exp).fillna(0), self.order)
            if not df_exp.empty:
                df = df.add(-df_exp, fill_value=0)

                # Production + import - exports
            alldf["Primary energy supply " + self.unitname] = (
                self.com_order(df, self.order) * self.unitc
            )

            # 4.2) Useful consumption
            tecs = list(
                set(self.scenario.par("output", {"level": ["useful"]}).technology)
            )
            df, df2 = self.model_output(tecs, current_node, "output")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            alldf["Useful energy " + self.unitname] = df * self.unitc

            # 4.3) Final energy consumption
            # Final energy consumption by source
            tecs = list(
                set(self.scenario.par("output", {"level": ["final"]}).technology)
            )
            df, df2 = self.model_output(tecs, current_node, "output")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Final energy consumption " + self.unitname] = df * self.unitc

            # 5) Energy trade
            # 5.1) Exports
            df, df2 = self.model_output(tecs_exp, current_node, "output")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs_exp, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Energy exports " + self.unitname] = df * self.unitc

            # 5.2) Imports
            df, df2 = self.model_output(tecs_imp, current_node, "output")
            df = self.group(df, ["year_act", "commodity"], "product", 0.0, yr)
            # adding historical data
            df_hist = self.add_history(tecs_imp, current_node, df2, "commodity")
            df = self.com_order((df_hist + df).fillna(0), self.order)
            alldf["Energy imports " + self.unitname] = df * self.unitc

            # 6) Emissions
            ems = ["TCE"]
            df1 = self.scenario.var("EMISS", {"emission": ems, "node": current_node})
            alldf["Total GHG emissions (MtCeq)"] = self.group(
                df1, ["year", "emission"], "lvl", 0.0, yr
            )

            # 7) Plotting

            plt.style.use("ggplot")

            # Setting tick width
            plt.rcParams["xtick.major.size"] = self.ticksz
            plt.rcParams["xtick.major.width"] = self.tickwdt
            plt.rcParams["ytick.major.size"] = self.ticksz
            plt.rcParams["ytick.major.width"] = self.tickwdt
            plt.rcParams["axes.linewidth"] = 0.1

            # Creating a pdf file for receiving the results
            # Selecting the plots to be plotted
            if plots != "all":
                keys = [
                    x for x in self.dict_plot.keys() if any([y in x for y in plots])
                ]
                self.dict_plot = {x: self.dict_plot[x] for x in keys}
            keys = [
                x for x in self.dict_plot.keys() if not any([y in x for y in not_plots])
            ]
            self.dict_plot = {x: self.dict_plot[x] for x in keys}
            with PdfPages(
                path
                + "\\{}-msgResults.pdf".format(
                    case
                    + f"_{current_node}_"
                    + time.strftime("%m.%d_%H.%M", time.localtime())
                )
            ) as pdf:
                j = 0
                for subplt, item in self.dict_plot.items():
                    df = alldf[subplt].copy()
                    kind = item
                    j = j + 1
                    if df.empty:
                        continue
                    # Renaming
                    df.rename(self.renaming, axis=1, inplace=True)

                    # Adding up columns with the same name
                    df = df.groupby(level=0, axis=1).sum()

                    # Writing to Excel
                    sh_name = (
                        subplt.replace("[", "(").replace("]", ")").replace("/", "")
                    )
                    if len(sh_name.split(": ")) > 1:
                        sh_name = sh_name.split(": ")[1]
                    df.to_excel(writer_xls, sheet_name=sh_name)

                    # Plotting
                    fig = plt.figure(j)
                    ax = fig.add_subplot(111)
                    box = ax.get_position()

                    if subplt in ["Power plant new capacity " + self.unitname_cap]:
                        ax.set_position(
                            [box.x0, box.y0, box.width * 0.8, box.height * 0.6]
                        )
                    else:
                        df = df.loc[(df.index >= yr_min) & (df.index <= yr_max)]
                        ax.set_position(
                            [box.x0, box.y0, box.width * 0.6, box.height * 0.6]
                        )

                        # Removing those values lower than min data for plots
                    df = df.loc[:, (df > max(df.max()) * self.min_val).any()]
                    df = df.loc[:, (df > self.min_abs).any()]

                    if df.empty:
                        print(
                            "> WARNING: There is no solution data in the selected"
                            " years and limits to be plotted for {}!".format(subplt)
                        )
                        continue
                    # indices = np.linspace(0, cmap.N, len(dfs.columns))
                    # my_colors = [cmap(int(i)) for i in indices]
                    my_colors = [self.color_map.get(x) for x in df.columns]
                    my_colors = ["peru" if i == None else i for i in my_colors]
                    df.index.name = None
                    plt_title = f"{subplt} in {self.abbrev_prov[current_node]}"
                    df.plot(
                        ax=ax,
                        kind=kind,
                        stacked=True,
                        color=my_colors,
                        grid=None,
                        title=plt_title,
                        linewidth=self.lw,
                        width=0.75,
                    )

                    # plt.ylabel(subplt, size=fntsz, color=fntcol)
                    plt.title(plt_title, size=self.fntsz * 2, color=self.fntcol)
                    handles, labels = ax.get_legend_handles_labels()

                    plt.tick_params(axis="both", which="major", labelsize=self.fntsz)
                    plt.grid(
                        visible=True,
                        which="both",
                        linewidth=0.1,
                        color="silver",
                        linestyle="-",
                    )
                    ax.set_xticklabels(df.index, rotation=30)

                    # Put a legend to the right of the current axis
                    ax.legend(
                        handles[::-1],
                        labels[::-1],
                        loc="center left",
                        bbox_to_anchor=(1, 0.5),
                        fontsize=self.fntsz * 1,
                    )

                    alldf[subplt] = df
                    pdf.savefig()
                    plt.show()
                    plt.close()
            # Savig Excel file
            writer_xls.close()
        os.chdir(cwd)
        return alldf
