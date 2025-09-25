import pandas as pd
import requests
import os
import math


class CODERS_pull:
    """
    Class containing the functions related to pulling CODERS data for use
    in the MESSAGE model. Requries an API key to be passed
    """

    def __init__(self, key):
        self.key = key
        self.url = "http://206.12.95.102/"
        self.root = os.path.dirname(os.path.dirname(os.getcwd()))

    def create_generation_generic(self):
        """
        Pulls the generation_generic data from CODERS,
        returns the data in a dataframe
        """
        query = f"{self.url}/generation_generic?key={self.key}"
        gen_generic = pd.DataFrame.from_dict(requests.get(query).json())
        gen_generic = gen_generic.set_index(gen_generic["gen_type"], drop=True)
        tech_names = pd.read_csv("CODERS-MESSAGE_technologies.csv", index_col=1)
        gen_generic = gen_generic.join(tech_names)
        gen_generic["year"] = 2020
        return gen_generic

    def generator_costs(self, gen_generic):
        """
        Pulls the cost data from CODERS and formats it into MESSAGE format,
        saves the result in a csv file
        """
        costs = gen_generic[["MESSAGE_tech", "year"]]
        costs["capital_cost_USD_per_kW"] = gen_generic["capital_cost_CAD_per_kW"] / 1.3
        costs["fixed_om_cost_USD_per_MWyear"] = (
            gen_generic["fixed_om_cost_CAD_per_MWyear"] / 1.3
        )
        costs["variable_om_cost_USD_per_MWh"] = (
            gen_generic["variable_om_cost_CAD_per_MWh"] / 1.3
        )
        costs.to_csv(f"{self.root}\\data\\CODERS_data\\generator_costs.csv")

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
            # Fixing coders bugs
            if data.gen_type == "wind_onshore":
                gentype = "wind_ons"
            elif data.gen_type == "solar_pv":
                gentype = "solar_PV"
            elif data.gen_type == "gas_CT":
                gentype = "NG_SC"
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
            f"{self.root}\\data\\CODERS_data\\generation_capacity_national.csv"
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
                provincial_capacity[name] = (
                    generators_year.groupby(["MESSAGE_tech"])
                    .sum()
                    .unit_installed_capacity
                )
        pd.DataFrame.from_dict(provincial_capacity).to_csv(
            f"{self.root}\\data\\CODERS_data\\generation_capacity_provincial.csv"
        )

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
            f"{self.root}\\data\\CODERS_data\\historical_capacity_raw_CODERS.xlsx"
        )


if __name__ == "__main__":
    pull = CODERS_pull("vBiOGBwJ3hwNLpqh")
    generation_generic = pull.create_generation_generic()
    pull.generator_costs(generation_generic)
    generators = pull.calculate_closure_years(generation_generic)
    # pull.generation_capacity_national(generators, 2020, 2050)
    # pull.generation_capacity_provincial(generators, 2020, 2050)
    pull.MESSAGE_historical_capacity_raw(generators, [2015, 2020])
