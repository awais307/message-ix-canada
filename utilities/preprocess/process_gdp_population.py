import pandas as pd
import numpy as np
from pathlib import Path

def process_gdp_population_data(path_to_gdp,path_to_pop):
    """
    Process GDP and population data for the model.
    
    Args:
        path_to_pop (str or Path): Path to the CSV file containing raw population data.
        path_to_gdp (str or Path): Path to the CSV file containing raw GDP data.
    
    Returns:
        pd.DataFrame: DataFrame containing processed GDP, population, and GDP per capita data for each province.
    """
    path_to_gdp = Path(path_to_gdp).resolve()
    path_to_pop = Path(path_to_pop).resolve()
    
    ssp_gdp_df = pd.read_csv(path_to_gdp)
    ssp_pop_df = pd.read_csv(path_to_pop)
    ssp_pop_df['Population'] = ssp_pop_df['Population'] * 1000
    ssp_pop_df['Province'] = ssp_pop_df['Province'].str.replace(' ', '')

    # Adjusting province names for consistency
    province_mapping = {
    'Newfoundland and Labrador': 'NewfoundlandandLabrador',
    'Prince Edward Island': 'PrinceEdwardIsland'
    }
    ssp_pop_df['Province'] = ssp_pop_df['Province'].replace(province_mapping)

    # List of provinces from the data
    provinces = ssp_gdp_df['Province'].unique()

    ssp_df = []
    for province in provinces:
        c_ssp_gdp_df = ssp_gdp_df.loc[ssp_gdp_df.Province == province]
        c_ssp_pop_df = ssp_pop_df.loc[ssp_pop_df.Province == province]
        # empty gdp dataframe
        gdp = []
        # empty population dataframe
        pop = []
        # empty gdp per capita dataframe
        gdpc = []

        for jjj in [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]:
            if not c_ssp_gdp_df.loc[c_ssp_gdp_df.Year == jjj].empty and not c_ssp_pop_df.loc[c_ssp_pop_df.Year == jjj].empty:
                gdp.append(c_ssp_gdp_df.loc[c_ssp_gdp_df.Year == jjj, 'GDP'].values[0])
                pop.append(c_ssp_pop_df.loc[c_ssp_pop_df.Year == jjj, 'Population'].values[0])
                # calculate gdp per capita
                gdpc.append(gdp[-1] / pop[-1]) #gdp per capita
            else:
                gdp.append(np.nan)
                pop.append(np.nan)
                gdpc.append(np.nan)

        ssp_df.append(pd.DataFrame({
            'year': [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060],
            'gdp': gdp,
            'pop': pop,
            'gdpc': gdpc,
            'iso': province
        }))
    ssp_df = pd.concat(ssp_df)
    return ssp_df



def add_population_gdp_to_scenario(scenario, population_data, gdp_data):
    """
    Add processed population and GDP data to the scenario.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        population_data (pd.DataFrame): DataFrame containing processed population data.
        gdp_data (pd.DataFrame): DataFrame containing processed GDP data.
    
    Updates:
        Adds the processed population and GDP data to the scenario's 'bound_activity_lo' parameter.
    """
    population_data.rename(columns={'Population': 'value', 'Province': 'node_loc', 'Year': 'year_act'}, inplace=True)
    population_data['technology'] = 'Population'
    population_data['mode'] = 'P'
    population_data['time'] = 'year'
    population_data['unit'] = 'GWa/a'

    gdp_data.rename(columns={'GDP': 'value', 'Province': 'node_loc', 'Year': 'year_act'}, inplace=True)
    gdp_data['technology'] = 'GDP'
    gdp_data['mode'] = 'P'
    gdp_data['time'] = 'year'
    gdp_data['unit'] = 'GWa/a'

    concatenated_df_socio = pd.concat([population_data, gdp_data])

    df = scenario.par('bound_activity_lo')
    df_filtered = df[~df['technology'].isin(['Population', 'GDP'])]
    df_bound_new = pd.concat([df_filtered, concatenated_df_socio])

    scenario.check_out()
    scenario.add_par('bound_activity_lo', df_bound_new)
    scenario.commit('Added population and GDP bounds')