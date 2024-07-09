import pandas as pd
import numpy as np
from pathlib import Path

def process_population_data(path):
    """
    Process population data for the model.
    
    Args:
        data_path (str or Path): Path to the CSV file containing raw population data.
    
    Returns:
        pd.DataFrame: DataFrame containing processed population data.
    """
    data = pd.read_csv(path)
    data.rename(columns={'Unnamed: 0': 'Year'}, inplace=True)
    data['Year'] = pd.to_datetime(data['Year'], format='%Y')
    pivoted_data = data.melt(id_vars=['Year'], var_name='Province', value_name='Population')
    pivoted_data.set_index('Year', inplace=True)
    pivoted_data.sort_index(inplace=True)
    pivoted_data['Population'] = pivoted_data['Population'].ffill().bfill()
    resampled_data = pivoted_data.groupby('Province').resample('5A').mean().interpolate(method='linear')
    resampled_data = resampled_data.reset_index()
    resampled_data['Year'] = resampled_data['Year'].dt.year - 1
    resampled_data['Province'] = resampled_data['Province'].str.replace(' ', '')
    return resampled_data

def process_gdp_data(dpath):
    """
    Process GDP data for the model.
    
    Args:
        data_path (str or Path): Path to the CSV file containing raw GDP data.
    
    Returns:
        pd.DataFrame: DataFrame containing processed GDP data.
    """
    df_gdp = pd.read_csv(path)
    gdp_data = df_gdp.melt(id_vars=['prov'], var_name='Year', value_name='GDP')
    gdp_data.rename(columns={'prov': 'Province'}, inplace=True)
    gdp_data['Province'] = gdp_data['Province'].str.replace(' ', '')
    return gdp_data

def add_population_gdp_to_scenario(scenario, population_data, gdp_data):
    """
    Add processed population and GDP data to the scenario.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        population_data (pd.DataFrame): DataFrame containing processed population data.
        gdp_data (pd.DataFrame): DataFrame containing processed GDP data.
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