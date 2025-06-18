import pandas as pd
import numpy as np
import requests
import os
import math


class CODERS_pull:
    """
    Class containing the functions related to pulling CODERS data for use
    in the MESSAGE model. Requries an API key to be passed
    """

    def __init__(self, key_file):
        self.url = "http://206.12.97.113/"  #'http://206.12.95.102/'
        self.root = os.path.dirname(os.path.dirname(os.getcwd()))
        with open(key_file, "r") as key:
            self.key = key.readline().strip()

        self.abbrev_prov = {
            "AB": "Alberta",
            "BC": "BritishColumbia",
            "SK": "Saskatchewan",
            "MB": "Manitoba",
            "ON": "Ontario",
            "QC": "Quebec",
            "NB": "NewBrunswick",
            "NL": "NewfoundlandandLabrador",
            "PE": "PrinceEdwardIsland",
            "NS": "NovaScotia",
            "YT": "Yukon",
            "NT": "NorthwestTerritories",
            "NU": "Nunavut",
        }

    def MESSAGE_table(self, table: pd.DataFrame, type="activity") -> pd.DataFrame:

        if type == "activity":
            ha_columns = [
                "node_loc",
                "technology",
                "year_act",
                "mode",
                "time",
                "value",
                "unit",
            ]
            msg_table = pd.DataFrame(columns=ha_columns)

            for idx in table.index:
                for col in table.columns:
                    msg_table.loc[len(msg_table)] = [
                        self.abbrev_prov[col.split("_")[0]],  # node
                        idx,  # technology
                        int(col.split("_")[1]),  # year
                        "M1",  # mode
                        "year",  # time
                        table.at[idx, col],  # value
                        "GWa/a",  # unit
                    ]

        return msg_table

    def create_generation_generic(self):
        """
        Pulls the generation_generic data from CODERS,
        returns the data in a dataframe
        """
        query = f"{self.url}/generation_generic?key={self.key}"
        gen_generic = pd.DataFrame.from_dict(requests.get(query).json())
        gen_generic = gen_generic.set_index(gen_generic["gen_type"], drop=True)
        tech_names = pd.read_csv("data/CODERS-MESSAGE_technologies.csv", index_col=1)
        gen_generic = gen_generic.join(tech_names)
        gen_generic["year"] = 2020
        return gen_generic

    def generator_costs(self, gen_generic):
        """
        Pulls the cost data from CODERS and formats it into MESSAGE format,
        saves the result in a csv file
        """
        costs = gen_generic[["MESSAGE_tech", "year"]]
        costs["capital_cost_USD_per_kW"] = (
            gen_generic["capital_cost_CAD_per_kW"].astype(float) / 1.3
        )
        costs["fixed_om_cost_USD_per_MWyear"] = (
            gen_generic["fixed_om_cost_CAD_per_MWyear"].astype(float) / 1.3
        )
        costs["variable_om_cost_USD_per_MWh"] = (
            gen_generic["variable_om_cost_CAD_per_MWh"].astype(float) / 1.3
        )
        costs.to_csv(f"data\\CODERS_data\\generator_costs.csv")

    def calculate_closure_years(self, gen_generic):
        """
        Calculates the retirement years for all generators missing that data in CODERS,
        adds the service_life parameter to the start_year parameter.
        Returns the resulting generator data in a dataframe
        """
        query = f"{self.url}/generators?key={self.key}"
        generators = pd.DataFrame.from_dict(requests.get(query).json())
        generators = generators.set_index(generators["generation_unit_name"], drop=True)

        # Fixing NaN closure years and generator types
        closure_year = {}
        updated_gen_type = {}
        for unit, data in generators.iterrows():
            """
            # Fixing coders bugs from old API address
            if data.gen_type == 'wind_onshore':
                    gentype = 'wind_ons'
            elif data.gen_type == 'solar_pv':
                    gentype = 'solar_PV'
            elif data.gen_type == 'gas_CT':
                    gentype = 'NG_SC'
            """
            # Fixing coders bugs from new API address
            if data.gen_type == "wind_ons":
                gentype = "wind_onshore"
            elif data.gen_type == "Biomass":
                gentype = "biomass"
            else:
                gentype = data.gen_type

            if math.isnan(data.closure_year):
                closure_year[unit] = (
                    data.start_year + gen_generic.at[gentype, "service_life"]
                )
            else:
                closure_year[unit] = data.closure_year
            updated_gen_type[unit] = gentype
        generators["updated_closure_year"] = pd.Series(closure_year)
        generators["updated_gen_type"] = pd.Series(updated_gen_type)
        generators = pd.merge(
            generators,
            gen_generic["MESSAGE_tech"],
            left_on="updated_gen_type",
            right_index=True,
        )
        return generators

    def generation_capacity_national(self, generators, startyear=2000, endyear=2050):
        """
        Calculates the active national capacity for every year between the start and end years,
        saves to a csv file
        """
        national_capacity = {}
        for year in range(startyear, endyear + 1):
            generators_year = generators[generators.start_year <= year].copy()
            generators_year = generators_year[
                generators_year.updated_closure_year > year
            ]
            national_capacity[year] = (
                generators_year.groupby(["MESSAGE_tech"]).sum().unit_installed_capacity
            )
        pd.DataFrame.from_dict(national_capacity).to_csv(
            f"data/CODERS_data/generation_capacity_national.csv"
        )

    def generation_capacity_provincial(self, generators, startyear=2000, endyear=2050):
        """
        Calculates active capacity for each province, for every year between the start and end years,
        saves to a csv file
        """
        provinces = generators.province.unique()
        # Calculating capacity for each province
        provincial_capacity = {}
        for prov in provinces:
            generators_prov = generators[generators["province"] == prov].copy()
            for year in range(startyear, endyear + 1):
                generators_year = generators_prov[generators_prov.start_year <= year]
                generators_year = generators_year[
                    generators_year.updated_closure_year > year
                ]
                name = f"{prov}_{year}"
                generators_year.unit_installed_capacity = (
                    generators_year.unit_installed_capacity.astype(float)
                )  # converting column to float type
                provincial_capacity[name] = (
                    generators_year.groupby(["MESSAGE_tech"])
                    .sum()
                    .unit_installed_capacity.astype(float)
                )
        provincial_capacity = pd.DataFrame.from_dict(provincial_capacity)
        provincial_capacity.fillna(0, inplace=True)
        provincial_capacity.to_csv(
            f"data/CODERS_data/generation_capacity_provincial.csv", sep=","
        )
        return (
            pd.DataFrame.from_dict(provincial_capacity),
            provincial_capacity,
        )  # return for debugging purposes

    def MESSAGE_historical_capacity_raw(self, generators, years=[2015, 2020]):
        """
        Calculates the generation capacity active at each year passed to the function,
        saves results in an excel file
        """
        generators["region-technology"] = (
            generators["operating_region"] + "-" + generators["MESSAGE_tech"]
        )
        i = 0
        for year in years:
            generators_year = generators[generators.start_year <= year]
            generators_year = generators_year[
                generators_year.updated_closure_year > year
            ]
            gen_prov_tech = pd.DataFrame(
                generators_year.groupby(["region-technology"])
                .sum()
                .unit_installed_capacity
            )
            # Calculate national capacity
            for tech in generators["MESSAGE_tech"]:
                name = f"Canada-{tech}"
                gen_prov_tech.loc[name] = (
                    generators.groupby(["MESSAGE_tech"])
                    .sum()
                    .unit_installed_capacity.loc[tech]
                )
            gen_prov_tech = gen_prov_tech.reset_index()
            gen_prov_tech[["region", "technology"]] = gen_prov_tech[
                "region-technology"
            ].str.split("-", expand=True)

            gen_prov_tech = gen_prov_tech.set_index(gen_prov_tech["region"], drop=True)
            gen_prov_tech["year"] = year
            gen_prov_tech["unit"] = "Gwa"
            gen_prov_tech["value"] = gen_prov_tech["unit_installed_capacity"] / 1000
            gen_prov_tech = gen_prov_tech[["technology", "year", "value", "unit"]]
            if i == 0:
                result = gen_prov_tech
                i += 1
            else:
                result = pd.concat([result, gen_prov_tech])

        pd.DataFrame.from_dict(result).to_excel(
            f"data/CODERS_data/historical_capacity_raw_CODERS.xlsx"
        )

    def historical_activity(
        self,
        generators,
        startyear=2014,
        endyear=2021,
        filename="historical_activity_provincial",
    ):
        """
        Creates historical activity CSV.

        Units

        facility_average_annual_energy. [CODERS]: GWh/year
        provincial_activity [output]: GW
        """
        provinces = generators.province.unique()
        generators["activity"] = generators.facility_average_annual_energy.astype(
            float
        )  # * generators.capacity_factor.astype(float)
        # Calculating historical activity for each province
        provincial_activity = {}
        for prov in provinces:
            generators_prov = generators[generators["province"] == prov].copy()
            for year in range(startyear, endyear + 1):
                generators_year = generators_prov[generators_prov.start_year <= year]
                generators_year = generators_year[
                    generators_year.updated_closure_year > year
                ]
                name = f"{prov}_{year}"
                provincial_activity[name] = (
                    generators_prov.groupby(["MESSAGE_tech"]).sum().activity
                )

        provincial_activity = pd.DataFrame.from_dict(provincial_activity)
        provincial_activity.fillna(0, inplace=True)
        provincial_activity = (
            provincial_activity / 8760
        )  # Conversion from GWh/year to GW
        provincial_activity = self.MESSAGE_table(provincial_activity)
        provincial_activity.round(4).to_csv(
            f"data/CODERS_data/{filename}.csv", sep=",", index=False
        )

        return provincial_activity

    def get_capacity_factors(
        self,
        generators,
        startyear=2000,
        endyear=2050,
        filename="capacity_factors_provincial",
    ):

        provinces = generators.province.unique()
        tech_capacity_factors = {}

        for prov in provinces:
            generators_prov = generators[generators["province"] == prov].copy()
            for year in range(startyear, endyear + 1):
                avg_cap_factors = []
                generators_year = generators_prov[generators_prov.start_year <= year]
                generators_year = generators_year[
                    generators_year.updated_closure_year > year
                ]
                name = f"{prov}_{year}"
                tech_capacity_factors[name] = generators_prov.groupby(
                    ["MESSAGE_tech"]
                ).capacity_factor.unique()

        prov_capacity_factors = pd.DataFrame.from_dict(tech_capacity_factors)
        prov_capacity_factors = prov_capacity_factors.applymap(
            lambda x: (
                sum([float(i) for i in x]) / len(x) if isinstance(x, np.ndarray) else x
            )
        )
        prov_capacity_factors.fillna(0, inplace=True)
        prov_capacity_factors.round(4).to_csv(
            f"data/CODERS_data/{filename}.csv", sep=","
        )
        return prov_capacity_factors
