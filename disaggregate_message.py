import pandas as pd
import json
from pathlib import Path
from urllib.request import urlopen
from collections import defaultdict
from datetime import datetime, timedelta
import subprocess
import os
import random
import math
import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as tkmb
from collections import defaultdict
import configparser


API_KEY = ""
BASE_DIR = Path(__file__).resolve().parent

message_to_coders_conversion = {
    '': 'total',
    'Biomass': 'total_biomass',
    'Biomass|w/ CCS': 'biomass_CCS',
    'Biomass|w/o CCS': 'biomass',
    'Coal': 'total_coal',
    'Coal|w/ CCS': 'coalCCS',
    'Coal|w/o CCS': 'coal',
    'Gas': 'total_gas',
    'Gas|w/ CCS': 'NG_CCS',
    'Gas|w/o CCS': 'NG_CC',
    'Geothermal': 'geothermal',
    'Hydro': 'hydro_run',
    'Nuclear': 'nuclear',
    'Oil': 'total_oil',
    'Oil|w/ CCS': 'diesel',
    'Oil|w/o CCS': 'diesel',
    'Solar': 'total_solar',
    'Solar|CSP': 'solar',
    'Solar|PV': 'solar',
    'Storage': 'storage_LI',
    'Wind': 'total_wind',
    'Wind|Offshore': 'wind_ofs',
    'Wind|Onshore': 'wind_ons'
}


def fetch_json_from_api(endpoint):
    with urlopen(f"https://api.sesit.ca/{endpoint}?key={API_KEY}") as response:
        return json.loads(response.read())


def load_generators_data():
    gen_data = pd.json_normalize(fetch_json_from_api("generators"))
    storage_data = pd.json_normalize(fetch_json_from_api("storage"))

    storage_data.rename(columns={
        'storage_facility_name': 'generation_unit_name',
        'storage_code': 'generation_unit_code',
        'connecting_voltage_in_kv': 'connecting_voltage',
        'storage_type': 'gen_type',
        'storage_type_copper': 'gen_type_copper',
        'storage_capacity': 'unit_installed_capacity'
    }, inplace=True)

    generators = pd.concat([gen_data, storage_data], ignore_index=True)

    generators['copper_balancing_area'] = generators['copper_balancing_area'].str.lower()
    generators['unit_installed_capacity'] = generators['unit_installed_capacity'].astype(float)
    generators['latitude'] = generators['latitude'].astype(float)
    generators['longitude'] = generators['longitude'].astype(float)
    return generators


def analyze_generator_distribution(generators):
    def print_distribution(gen_list, label):
        total = len(gen_list)
        counts = gen_list['gen_type_copper'].value_counts()
        percentages = (counts / total) * 100
        print(f"\n{label} generator type percentages (based on count):")
        for gen_type, count in counts.items():
            print(f"{gen_type}: {count} generators ({percentages[gen_type]:.2f}%)")

    print_distribution(generators[generators['gen_type_copper'].isin(['hydro_daily', 'hydro_run', 'hydro_monthly'])], 'Hydro')
    print_distribution(generators[generators['gen_type_copper'].isin(['oil_ST', 'oil_CT'])], 'Oil')
    print_distribution(generators[generators['gen_type_copper'].isin(['storage_LI', 'storage_PH'])], 'Storage')

def process_messageix_file(filepath):
    df = pd.read_excel(filepath)
    
    df_filtered = df[df["Variable"].str.contains(r"^Capacity\|Electricity(?!.*\|\d+$)", na=False)].copy()

    # Add MESSAGE -> CODERS conversion
    conversion_with_prefix = {
        'Capacity|Electricity|' + k if k != '' else 'Capacity|Electricity': v
        for k, v in message_to_coders_conversion.items()
    }
    df_filtered['gen_type_coders'] = df_filtered['Variable'].map(conversion_with_prefix)
    df_filtered.to_csv('message_with_total.csv', index=False)
    

    df_filtered = df_filtered[~df_filtered["gen_type_coders"].str.contains("total", na=False)]
    df_filtered.to_csv('message_without_total.csv', index=False)
    

    df_filtered['Region'] = df_filtered['Region'].str.lower().str.replace(' ', '', regex=True)
    df_filtered.to_csv('message_ungrouped.csv', index=False)

    year_cols = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]
    # year_cols = [2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]

    df_grouped = df_filtered.groupby(['Region', 'Scenario', 'gen_type_coders'])[year_cols].sum().reset_index()
    df_grouped.to_csv('message_grouped.csv', index=False)

    storage_li_rows = df_grouped[df_grouped['gen_type_coders'] == 'storage_LI'].copy()
    if not storage_li_rows.empty:
        storage_ph_rows = storage_li_rows.copy()
        storage_ph_rows['gen_type_coders'] = 'storage_PH'
        for year in year_cols:
            storage_li_rows.loc[:, year] = storage_li_rows[year] * 0.98
            storage_ph_rows.loc[:, year] = storage_ph_rows[year] * 0.02
        df_grouped = df_grouped[df_grouped['gen_type_coders'] != 'storage_LI']
        df_grouped = pd.concat([df_grouped, storage_li_rows, storage_ph_rows], ignore_index=True)

    hydro_run_rows = df_grouped[df_grouped['gen_type_coders'] == 'hydro_run'].copy()
    if not hydro_run_rows.empty:
        hydro_daily_rows = hydro_run_rows.copy()
        hydro_monthly_rows = hydro_run_rows.copy()
        hydro_daily_rows['gen_type_coders'] = 'hydro_daily'
        hydro_monthly_rows['gen_type_coders'] = 'hydro_monthly'
        for year in year_cols:
            hydro_run_rows.loc[:, year] = hydro_run_rows[year] * 0.418
            hydro_daily_rows.loc[:, year] = hydro_daily_rows[year] * 0.414
            hydro_monthly_rows.loc[:, year] = hydro_monthly_rows[year] * 0.168
        df_grouped = df_grouped[df_grouped['gen_type_coders'] != 'hydro_run']
        df_grouped = pd.concat([df_grouped, hydro_run_rows, hydro_daily_rows, hydro_monthly_rows], ignore_index=True)

    # --- Process 'oil_ST' into 20% 'oil_ST' and 80% 'oil_CT'
    oil_st_rows = df_grouped[df_grouped['gen_type_coders'] == 'oil_ST'].copy()
    if not oil_st_rows.empty:
        oil_ct_rows = oil_st_rows.copy()
        oil_ct_rows['gen_type_coders'] = 'oil_CT'
        for year in year_cols:
            oil_st_rows.loc[:, year] = oil_st_rows[year] * 0.2
            oil_ct_rows.loc[:, year] = oil_ct_rows[year] * 0.8
        df_grouped = df_grouped[df_grouped['gen_type_coders'] != 'oil_ST']
        df_grouped = pd.concat([df_grouped, oil_st_rows, oil_ct_rows], ignore_index=True)

    return df_grouped


def prepare_generators_for_merge(generators):
    df = generators[['gen_type_copper', 'unit_installed_capacity', 'operating_region']].copy()

    # Clean strings
    df['gen_type_copper'] = df['gen_type_copper'].str.strip().str.lower()
    df['operating_region'] = df['operating_region'].str.strip().str.lower().str.replace(' ', '', regex=True)

    # Drop rows with missing or zero capacity
    df = df[df['unit_installed_capacity'].notnull()]
    df = df[df['unit_installed_capacity'] > 0]

    # Group and sum
    grouped = df.groupby(['gen_type_copper', 'operating_region'], as_index=False)['unit_installed_capacity'].sum()

    return grouped


def compare_message_and_coders(message_df, generators_grouped,  year):
    year = int(year)
    if year not in message_df.columns:
        raise ValueError(f"Year {year} not found in message_df columns")
    message_filtered = message_df[['gen_type_coders', year, 'Region']].copy()
    message_grouped = message_filtered.groupby(['gen_type_coders', 'Region'], as_index=False).sum()

    message_grouped['gen_type_coders'] = message_grouped['gen_type_coders'].str.lower()
    message_grouped['Region'] = message_grouped['Region'].str.lower()
    generators_grouped['gen_type_copper'] = generators_grouped['gen_type_copper'].str.lower()
    generators_grouped['operating_region'] = generators_grouped['operating_region'].str.lower()

    # Unique values in 'gen_type' column of message_df
    unique_message_gen_types = message_grouped['gen_type_coders'].unique()

    # Unique values in 'gen_type' column of generators_grouped
    unique_grouped_gen_types = generators_grouped['gen_type_copper'].unique()

    print("Unique gen_type values in message_df:")
    print(unique_message_gen_types)

    print("\nUnique gen_type values in generators_grouped:")
    print(unique_grouped_gen_types)


    merged_df = message_grouped.merge(
        generators_grouped,
        left_on=['gen_type_coders', 'Region'],
        right_on=['gen_type_copper', 'operating_region'],
        how='outer'
    )
    merged_df.fillna({'unit_installed_capacity': 0, year: 0}, inplace=True)
    # Copy values across columns when missing (both directions)
    merged_df['Region'] = merged_df['Region'].fillna(merged_df['operating_region'])
    merged_df['operating_region'] = merged_df['operating_region'].fillna(merged_df['Region'])

    merged_df['gen_type_coders'] = merged_df['gen_type_coders'].fillna(merged_df['gen_type_copper'])
    merged_df['gen_type_copper'] = merged_df['gen_type_copper'].fillna(merged_df['gen_type_coders'])
    merged_df[f'message_{year}'] = merged_df[year] * 1000
    merged_df['dif'] = merged_df[f'message_{year}'] - merged_df['unit_installed_capacity']
    return merged_df



def select_options(options, message):
        selected_options = []

        def close_window():
            nonlocal selected_options
            selected_options = [listbox.get(idx) for idx in listbox.curselection()]
            root.destroy()

        root = tk.Tk()
        root.geometry("400x250")
        root.attributes('-topmost', True)
        root.title(message)
        listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, bd=5)
        for option in options:
            listbox.insert(tk.END, option)
            # listbox.selection_set(tk.END)  # Select all options by default

        listbox.pack(padx=10, pady=10)

        button = tk.Button(root, text="OK", command=close_window)
        button.pack(pady=5)

        root.mainloop()

        return selected_options

def remove_excess_generation_capacity(generators_df, excess_capacity, generation_type):
    """
    Remove excess generation capacity from the specified generator type in the DataFrame.

    Parameters:
        generators_df (DataFrame): DataFrame containing the generator data.
        excess_capacity (float): The amount of capacity to be removed.
        generation_type (str): The type of generation to be modified.

    Returns:
        DataFrame: Updated DataFrame with the removed excess capacity.
    """
    while excess_capacity > 0:
        # Find the oldest generator of the specified generation type
        old_gen = generators_df[(generators_df['gen_type_copper'] == generation_type)
                                & (generators_df['unit_installed_capacity'] > 0)].sort_values(
            by=['closure_year', 'possible_renewal_year'], ascending=True)
        
        if old_gen.empty:
            # generators_df.loc[generators_df['generation_facility_code'] == old_gen['generation_facility_code'], 'facility_installed_capacity'] = 0

            return generators_df
        
        else:
            old_gen = old_gen.iloc[0]

        if old_gen['unit_installed_capacity'] >= excess_capacity:
            # Reduce the capacity of the selected generator
            generators_df.at[old_gen.name, 'unit_installed_capacity'] -= excess_capacity

            new_facility_cap = generators_df.loc[generators_df['generation_facility_code'] == old_gen[
                'generation_facility_code']]['unit_installed_capacity'].sum()
            generators_df.loc[generators_df['generation_facility_code'] == old_gen[
                'generation_facility_code'], 'facility_installed_capacity'] = new_facility_cap

            return generators_df

        else:
            # Remove the entire capacity of the selected generator
            generators_df.at[old_gen.name, 'unit_installed_capacity'] = 0
            excess_capacity -= old_gen['unit_installed_capacity']

            new_facility_cap = generators_df.loc[generators_df['generation_facility_code'] == old_gen[
                'generation_facility_code']]['unit_installed_capacity'].sum()
            generators_df.loc[generators_df['generation_facility_code'] == old_gen[
                'generation_facility_code'], 'facility_installed_capacity'] = new_facility_cap

        if generators_df[generators_df['gen_type_copper'] == generation_type]['unit_installed_capacity'].sum() == 0:

            generators_df.loc[generators_df['generation_facility_code'] == old_gen[
                'generation_facility_code'], 'facility_installed_capacity'] = 0

            return generators_df

    return generators_df
def compute_yearly_average(input_df, output_file):

    df_numeric = input_df.drop(columns='h')

    # Compute average across 8760 rows (i.e., average per grid)
    averages = df_numeric.mean(axis=0)

    # Save the result to a CSV
    averages.to_frame(name='average_capacity_factor').to_csv(output_file, index_label='grid_id')

def add_renewable_potential(
    input_file: str,
    output_file: str,
    maxwind_ons_per: float = 2.5,
    maxwind_ofs_per: float = 2.5,
    maxsolar_per: float = 29.8
):
    """
    Reads a gridcells CSV file and adds three columns for wind (onshore & offshore)
    and solar potential capacity based on surface_area_ons and given max values.

    Parameters:
    - input_file: str - Path to input CSV file.
    - output_file: str - Path to save the output CSV with new columns.
    - maxwind_ons_per: float - Max onshore wind MW/km².
    - maxwind_ofs_per: float - Max offshore wind MW/km².
    - maxsolar_per: float - Max solar MW/km².
    """
    df = pd.read_csv(Path(__file__).resolve().parent / input_file)

    df['wind_ons_potential'] = df['surface_area_ons'] * maxwind_ons_per
    df['wind_ofs_potential'] = df['surface_area_ofs'] * maxwind_ofs_per
    df['solar_potential'] = df['surface_area_ons'] * maxsolar_per

    wind_cf = pd.read_csv(Path(__file__).resolve().parent / "windcf_avg.csv")
    solar_cf = pd.read_csv(Path(__file__).resolve().parent / "solarcf_avg.csv")

    # Rename columns for clarity
    solar_cf.columns = ['grid_cell', 'avg_solar_cf']
    wind_cf.columns = ['grid_cell', 'avg_wind_cf']

    # Ensure grid_cell column type matches
    df['grid_cell'] = df['grid_cell'].astype(int)
    solar_cf['grid_cell'] = solar_cf['grid_cell'].astype(int)
    wind_cf['grid_cell'] = wind_cf['grid_cell'].astype(int)

    # Merge average CFs into gridcell DataFrame
    df = df.merge(solar_cf, on='grid_cell', how='left')
    df = df.merge(wind_cf, on='grid_cell', how='left')

    df.to_csv(output_file, index=False)


def allocate_capacity_by_cf(gridcells_file: str, generators_necessary_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Allocate solar, wind_ons, and wind_ofs capacity to grid cells based on CF and potential.
    
    Parameters:
    - gridcells_file: str - Path to gridcells CSV with CF and potential data.
    - generators_necessary_df: pd.DataFrame - Contains 'dif' values for each region and tech.

    Returns:
    - pd.DataFrame containing only grid cells with some capacity allocated.
    """
    # Load and clean
    year = int(year)
    grid_df = pd.read_csv(gridcells_file)
    grid_df['pr'] = grid_df['pr'].str.strip().str.lower()
    generators_necessary_df['operating_region'] = generators_necessary_df['operating_region'].str.strip().str.lower()
    generators_necessary_df['gen_type_copper'] = generators_necessary_df['gen_type_copper'].str.strip().str.lower()

    # Initialize allocation columns
    grid_df['allocated_solar'] = 0.0
    grid_df['allocated_wind_ons'] = 0.0
    grid_df['allocated_wind_ofs'] = 0.0

    # Define configuration for each tech
    techs = {
        'solar': {
            'cf_column': 'avg_solar_cf',
            'potential_column': 'solar_potential',
            'allocation_column': 'allocated_solar',
        },
        'wind_ons': {
            'cf_column': 'avg_wind_cf',
            'potential_column': 'wind_ons_potential',
            'allocation_column': 'allocated_wind_ons',
        },
        'wind_ofs': {
            'cf_column': 'avg_wind_cf',
            'potential_column': 'wind_ofs_potential',
            'allocation_column': 'allocated_wind_ofs',
        }
    }

    for tech, cfg in techs.items():
        tech_df = generators_necessary_df[generators_necessary_df['gen_type_copper'] == tech]

        for region in tech_df['operating_region'].unique():
            region_dif_row = tech_df[tech_df['operating_region'] == region]
            if region_dif_row.empty:
                print(f"No data for region: {region} and tech: {tech}")
                continue

            dif = region_dif_row['dif'].values[0]

            if dif <= 0:
                print(f"Skipping region '{region}' for {tech} with non-positive dif: {dif}")
                continue

            print(f"Allocating {tech} for region '{region}' with dif = {dif}")

            region_grids = grid_df[grid_df['pr'] == region].copy()
            region_grids = region_grids.sort_values(by=cfg['cf_column'], ascending=False)

            for idx, row in region_grids.iterrows():
                potential = row[cfg['potential_column']]
                if potential <= 0 or dif <= 0:
                    print(f"Skipping grid {row['grid_cell']} in {region} due to potential={potential} or dif={dif}")
                    continue

                allocation = min(potential, dif)
                grid_df.at[idx, cfg['allocation_column']] = allocation
                dif -= allocation

                if dif <= 0:
                    break

    # Drop rows where no allocation was made
    df_filtered = grid_df[
        (grid_df["allocated_solar"] > 0) |
        (grid_df["allocated_wind_ons"] > 0) |
        (grid_df["allocated_wind_ofs"] > 0)
    ].copy()

    df_filtered["year"] = year
    df_filtered = df_filtered.rename(columns={
        "allocated_solar": "capacity_solar",
        "allocated_wind_ons": "capacity_wind_ons",
        "allocated_wind_ofs": "capacity_wind_ofs",
        "pr": "province"
    })

    final_df = df_filtered[
        ["year", "grid_cell", "capacity_solar", "capacity_wind_ons", "capacity_wind_ofs", "lon", "lat", "province"]
    ]

    return final_df



def get_wind_and_solar_capacity(generators_necessary, year):
    windcf = pd.read_csv(Path(__file__).resolve().parent / "windcf.csv")
    solarcf = pd.read_csv(Path(__file__).resolve().parent / "solarcf.csv")
    compute_yearly_average(solarcf, 'solarcf_avg.csv')
    compute_yearly_average(windcf, 'windcf_avg.csv')
    add_renewable_potential('gridcells.csv', 'gridcells_with_potential.csv')
    updated_gridcells = allocate_capacity_by_cf("gridcells_with_potential.csv", generators_necessary, year)
    updated_gridcells.to_csv('allthemerradata.csv', index=False)
    return updated_gridcells


def add_new_message_generators(existing_generators_df, new_generators_df, avg_gen_size_canada, vre_gen_types, min_gen_size):
    """
    Add new message generators to the existing generators DataFrame.

    Parameters:
        existing_generators_df (DataFrame): DataFrame containing existing generators data.
        new_generators_df (DataFrame): DataFrame containing new generators data.

    Returns:
        DataFrame: Updated DataFrame with added new generators.
    """
    # append new generators to existing generators
    new_generators_df.sort_values(by='dif', ascending=False, inplace=True)

    for index, row in new_generators_df.iterrows():

        generation_type = row['gen_type_copper']

        if generation_type not in vre_gen_types:

            if row['dif'] > 0:  # need new generators

                avg_size = existing_generators_df[existing_generators_df['gen_type_copper'] == generation_type]['unit_installed_capacity'].mean()

                # if no (or little) existing generation type in province, use canadian average or minimum gen size
                # (defined in disaggregate_generators function)
                if generation_type in avg_gen_size_canada:
                    avg_size = max(avg_gen_size_canada[generation_type], min_gen_size)
                else:
                    avg_size = min_gen_size
                num_needed = math.ceil(row['dif']/avg_size)

                facility_name = f'need_to_build_{row.province}_{row.gen_type_copper}_generator{random.randint(1,99999999999999)}'
                facility_node_code = f"please_assign_bus_in_{row.province}_{random.randint(1,99999999999999)}"
                facility_cap = row['dif']
                remaining_cap = row['dif']
                for new in range(num_needed):

                    new_size = min(avg_size, remaining_cap)

                    new_gen = {'generation_unit_code': f'need_to_build_{row.gen_type_copper}_generator{random.randint(1,99999999999999)}',
                                'generation_facility_code': facility_name, 'unit_installed_capacity': new_size,
                                'facility_installed_capacity': facility_cap,
                                'copper_balancing_area': row.province,
                                'gen_type': generation_type,
                                'network_node_code': facility_node_code,
                                'province':row.province,
                                'gen_type_copper': generation_type,
                                'operating_region': row.province,
                                # 'pre2025': row.pre2025
                                }

                    remaining_cap -= new_size
                    existing_generators_df.loc[len(existing_generators_df.index)] = new_gen

        if row['dif'] < 0:  # need to retire generators

            existing_generators_df = remove_excess_generation_capacity(existing_generators_df, -(row['dif']),
                                                                        row.gen_type_copper)

    existing_generators_df = existing_generators_df[existing_generators_df['unit_installed_capacity']>0]
    return existing_generators_df
def template_new_gen(row, type, new_gen_size):
    # silver doesnt currently support wind_ons or wind_ofs
    return {
        'generation_unit_code': f'need_to_build_{type}_generator{random.randint(1,99999999999999)}',
        'unit_installed_capacity': new_gen_size,
        'copper_balancing_area': row.province,
        'gen_type_copper': 'wind' if type in ['wind_ons', 'wind_ofs'] else 'solar',
        'gen_type': 'wind' if type in ['wind_ons', 'wind_ofs'] else 'solar',
        'operating_region': row.province,
        'latitude': row.lat,
        'longitude': row.lon,
        'network_node_code': f"please_assign_bus_{row.province}_{row.lat}_{row.lon}",
    }

def add_new_wind_ons(row, existing_generators, num_gen_needed, avg_gen_size):
    remaining_cap = row.capacity_wind_ons
    for _ in range(num_gen_needed):
        new_gen_size = min(avg_gen_size, remaining_cap)
        new_gen = template_new_gen(row, 'wind_ons', new_gen_size)
        remaining_cap -= new_gen_size
        existing_generators.loc[len(existing_generators.index)] = new_gen
    return existing_generators

def add_new_wind_ofs(row, existing_generators, num_gen_needed, avg_gen_size):
    remaining_cap = row.capacity_wind_ofs
    for _ in range(num_gen_needed):
        new_gen_size = min(avg_gen_size, remaining_cap)
        new_gen = template_new_gen(row, 'wind_ofs', new_gen_size)

        remaining_cap -= new_gen_size
        existing_generators.loc[len(existing_generators.index)] = new_gen
    return existing_generators

def add_new_solar(row, existing_generators, num_gen_needed, avg_gen_size):
    remaining_cap = row.capacity_solar
    for _ in range(num_gen_needed):
        new_gen_size = min(avg_gen_size, remaining_cap)
        new_gen = template_new_gen(row, 'solar', new_gen_size)

        remaining_cap -= new_gen_size
        existing_generators.loc[len(existing_generators.index)] = new_gen
    return existing_generators

def add_vre_generators(existing_generators, new_generators, avg_gen_size_canada):
    existing_generators.reset_index(drop=True, inplace=True)

    min_vre_gen_size = 10000

    # TODO: This function can likely be shortened a great deal by utilizing sub-functions
    for index, row in new_generators.iterrows():
        if row['capacity_wind_ons'] > 0:
            avg_gen_size = existing_generators[existing_generators['gen_type_copper'] ==
                                                      'wind_ons']['unit_installed_capacity'].mean()

            if avg_gen_size >= min_vre_gen_size:
                num_gen_needed = math.ceil(row['capacity_wind_ons']/avg_gen_size)
            else:
                # if no existing generation type in province, use canadian average or min VRE size
                # (defined in disaggregate_generators function)
                try:
                    size_used = max(avg_gen_size_canada['wind_ons'], min_vre_gen_size)
                except:
                    size_used = min_vre_gen_size
                num_gen_needed = math.ceil(row['capacity_wind_ons']/size_used)
                avg_gen_size = size_used

            existing_generators = add_new_wind_ons(row, existing_generators, num_gen_needed, avg_gen_size)

        if row['capacity_wind_ofs'] > 0:
            avg_gen_size = existing_generators[existing_generators['gen_type_copper'] ==
                                                      'wind_ofs']['unit_installed_capacity'].mean()

            if avg_gen_size >= min_vre_gen_size:
                num_gen_needed = math.ceil(row['capacity_wind_ofs']/avg_gen_size)
            else:
                # if no existing generation type in province, use canadian average or min VRE size
                # (defined in disaggregate_generators function)
                try:
                    size_used = max(avg_gen_size_canada['wind_ofs'], min_vre_gen_size)
                except:
                    size_used = min_vre_gen_size
                num_gen_needed = math.ceil(row['capacity_wind_ofs']/size_used)
                avg_gen_size = size_used

            existing_generators = add_new_wind_ofs(row, existing_generators, num_gen_needed, avg_gen_size)

        if row['capacity_solar'] > 0:  # TODO need to retire generators
            avg_gen_size = existing_generators[existing_generators['gen_type_copper'] ==
                                                      'solar']['unit_installed_capacity'].mean()

            if avg_gen_size >= min_vre_gen_size:
                num_gen_needed = math.ceil(row['capacity_solar']/avg_gen_size)

            else:
                # if no existing generation type in province, use canadian average or min VRE size
                # (defined in disaggregate_generators function)
                try:
                    size_used = max(avg_gen_size_canada['solar'], min_vre_gen_size)
                except:
                    size_used = min_vre_gen_size
                num_gen_needed = math.ceil(row['capacity_solar']/size_used)
                avg_gen_size = size_used

            existing_generators = add_new_solar(row, existing_generators, num_gen_needed, avg_gen_size)
    return existing_generators  
def append_merra_lat(lat):
    return round(2 * (lat + 90), 0) + 1

def append_merra_long(long):
    return round(1.6 * (long + 180), 0) + 1


def format_vre(solarcf, windcf, gridcells, vre_locs_merra, province, year):
    gridcells['lat_long'] = gridcells[['lat', 'lon']].astype(str).agg('_'.join, axis=1)
    gridcells_ref = gridcells['lat_long'].to_dict()
    gridcells_ref = {str(key): value for key, value in gridcells_ref.items()}

    gridcells['merra_lat'] = append_merra_lat(gridcells['lat']).astype(str)
    gridcells['merra_long'] = append_merra_long(gridcells['lon']).astype(str)
    gridcells['merra'] = gridcells[['merra_lat', 'merra_long']].agg('_'.join, axis=1)

    vre_locs_gridcells = list(set(gridcells.loc[gridcells['merra'].isin(vre_locs_merra)]['grid_cell'].astype(str)))
    vre_locs_gridcells.append('h')

    solarcf = solarcf[vre_locs_gridcells].copy()

    # adjust hour to be 0-indexed
    solarcf['h'] = solarcf['h'] - 1

    solarcf['time'] = year
    # using start year turn time column which has the hour of the year into the datetime format with date, year and hour
    solarcf['time'] = pd.to_datetime(solarcf['time'], format='%Y') + pd.to_timedelta(solarcf['h'], unit='h')
    solarcf.drop(columns='h', inplace=True)
    solarcf = solarcf.melt(id_vars='time', var_name='region', value_name='value')
    solarcf['variable'] = 'VRE Capacity Factor|Solar'
    solarcf = solarcf.groupby(['time', 'region', 'variable']).mean().reset_index()

    windcf = windcf[vre_locs_gridcells].copy()

    # adjust hour to be 0-indexed
    windcf['h'] = windcf['h'] - 1

    windcf['time'] = year
    # using start year turn time column which has the hour of the year into the datetime format with date, year and hour
    windcf['time'] = pd.to_datetime(windcf['time'], format='%Y') + pd.to_timedelta(windcf['h'], unit='h')
    windcf.drop(columns='h', inplace=True)
    windcf = windcf.melt(id_vars='time', var_name='region', value_name='value')
    windcf['variable'] = 'VRE Capacity Factor|Wind'
    windcf = windcf.groupby(['time', 'region', 'variable']).mean().reset_index()

    full_df = pd.concat([solarcf, windcf], ignore_index=True)
    full_df['region'] = full_df['region'].map(gridcells_ref)
    full_df['variable'] = full_df['variable'] + '|'+ full_df['region']
    full_df['region'] = province.capitalize()
    full_df['unit'] = '%'

    return full_df


def format_generators(existing_generators, province, year):
    # format disaggregated generators in IAMC formatting
    existing_generators['start_year'] = existing_generators['start_year'].fillna(year).astype(int).astype(str)
    # existing_generators['iamc_var'] = existing_generators[['gen_type_copper', 'generation_unit_code', 'start_year']].agg('|'.join, axis=1)
    existing_generators['iamc_var'] = existing_generators[['gen_type_copper', 'generation_unit_code', 'start_year']].astype(str).agg('|'.join, axis=1)


    cap_df = existing_generators[['iamc_var', 'operating_region', 'unit_installed_capacity']].copy()
    cap_df.rename(columns={'operating_region': 'region', 'unit_installed_capacity': 'value'}, inplace=True)
    cap_df['variable'] = 'Generators|Capacity|' + cap_df['iamc_var']
    cap_df['unit'] = 'MW'
    cap_df.drop(columns=['iamc_var'], inplace=True)

    node_df = existing_generators[['iamc_var', 'operating_region', 'network_node_code']].copy()
    node_df.rename(columns={'operating_region': 'region', 'network_node_code': 'value'}, inplace=True)
    node_df['variable'] = 'Generators|Node Code|' + node_df['iamc_var']
    node_df['unit'] = ''
    node_df.drop(columns=['iamc_var'], inplace=True)

    storage_gen_types = ["phs", "lb", "PHS", "LB", "storage_li", "storage_ph", "storage_ph", "storage_lb","storage_LI", "storage_PHS", "storage_LB", "storage_PH"]
    stor_df = existing_generators.loc[existing_generators['gen_type'].isin(storage_gen_types)]

    storeng_df = stor_df[['iamc_var', 'operating_region', 'storage_energy']].copy()
    storeng_df.rename(columns={'operating_region': 'region', 'storage_energy': 'value'}, inplace=True)
    storeng_df['variable'] = 'Generators|Storage Energy|' + storeng_df['iamc_var']
    storeng_df['unit'] = 'MWh'
    storeng_df.drop(columns=['iamc_var'], inplace=True)

    vre_df = existing_generators.loc[existing_generators['gen_type_copper'].isin(['solar', 'wind', 'wind_ons', 'wind_ofs'])].copy()
    vre_df['merra_lat'] = append_merra_lat(vre_df['latitude']).astype(str)
    vre_df['merra_long'] = append_merra_long(vre_df['longitude']).astype(str)
    vre_df['merra'] = vre_df[['merra_lat', 'merra_long']].agg('_'.join, axis=1)
    vre_locs_merra = list(set(vre_df['merra']))

    lat_df = vre_df[['iamc_var', 'operating_region', 'latitude']].copy()
    lat_df.rename(columns={'operating_region': 'region', 'latitude': 'value'}, inplace=True)
    lat_df['variable'] = 'Generators|Latitude|' + lat_df['iamc_var']
    lat_df['unit'] = ''
    lat_df.drop(columns=['iamc_var'], inplace=True)

    long_df = vre_df[['iamc_var', 'operating_region', 'longitude']].copy()
    long_df.rename(columns={'operating_region': 'region', 'longitude': 'value'}, inplace=True)
    long_df['variable'] = 'Generators|Longitude|' + long_df['iamc_var']
    long_df['unit'] = ''
    long_df.drop(columns=['iamc_var'], inplace=True)

    disaggregated_data = pd.concat([cap_df, node_df, storeng_df, lat_df, long_df], ignore_index=True)
    disaggregated_data['time'] = year
    disaggregated_data['region'] = province.capitalize()

    return disaggregated_data, vre_locs_merra

def format_iamc(existing_gens, solarcf, windcf, gridcells, province, year):
    gens_iamc, vre_locs_merra = format_generators(existing_gens, province, year)
    vre_iamc = format_vre(solarcf, windcf, gridcells, vre_locs_merra, province, year)

    all_iamc_data = pd.concat([gens_iamc, vre_iamc], ignore_index=True)

    return all_iamc_data



def generate_hourly_demand_profiles(input_csv, year, output_folder="output_hourly_demand"):
    # === Configuration ===
    output_folder = f"{output_folder}_{year}"
    os.makedirs(output_folder, exist_ok=True)

    # === Target variables ===
    target_variables = {
        "Final Energy|Industry|Electricity",
        "Final Energy|Residential and Commercial|Electricity",
        "Final Energy|Transportation|Electricity"
    }

    # === Conversion constant ===
    PJ_TO_MWH = 277777.78

    # === Load main data ===
    df = pd.read_excel(input_csv)
    df = df[df["Variable"].isin(target_variables)]

    # === Generate flat hourly demand for each row ===
    for idx, row in df.iterrows():
        region = row.get("Region")
        if pd.isna(region):
            print(f"⚠️ Skipping row {idx} due to missing region.")
            continue

        variable = row["Variable"]
        annual_demand_pj = row.get(year, None)  # Handle missing year column gracefully
        if pd.isna(annual_demand_pj):
            print(f"⚠️ Skipping row {idx} due to missing data for year {year}.")
            continue

        annual_demand_mwh = annual_demand_pj * PJ_TO_MWH
        hourly_demand = annual_demand_mwh / 8760

        # Create flat hourly profile
        output_df = pd.DataFrame({
            "hour_index": range(8760),
            "hourly_demand": [hourly_demand] * 8760,
            "Region": region,
            "Variable": variable,
            "Original_Unit": row.get("Unit", ""),
            "Converted_Unit": "MWh",
            "Scenario": row.get("Scenario", ""),
            "Model": row.get("Model", "")
        })

        # File name
        var_safe = variable.replace("|", "_").replace(" ", "")
        file_name = f"{region.replace(' ', '_')}_{var_safe}_hourly_demand.csv"
        output_path = os.path.join(output_folder, file_name)

        # Save to CSV
        output_df.to_csv(output_path, index=False)
        print(f"✅ Generated: {file_name}")
#     aggregate_hourly_demand_by_province(output_folder, year)

# def aggregate_hourly_demand_by_province(input_folder, year, output_folder=None):
#     """
#     Aggregates hourly electricity demand CSVs by province.

#     Parameters:
#     - input_folder (str): Path to folder containing individual hourly demand CSVs.
#     - output_folder (str): Optional. Where to save aggregated CSVs. Defaults to a subfolder named 'aggregated_by_province'.
#     """
    
#     if output_folder is None:
#         output_folder = os.path.join(input_folder, "aggregated_by_province")
#     output_folder = f"{output_folder}_{year}"
#     os.makedirs(output_folder, exist_ok=True)

#     province_dfs = defaultdict(list)

#     # Step 1: Group files by province
#     for filename in os.listdir(input_folder):
#         if filename.endswith(".csv"):
#             filepath = os.path.join(input_folder, filename)
#             province = filename.split('_')[0]
#             df = pd.read_csv(filepath)
#             province_dfs[province].append(df)

#     # Step 2: Aggregate each province's data
#     for province, dfs in province_dfs.items():
#         combined_df = pd.concat(dfs, ignore_index=True)
#         aggregated_df = combined_df.groupby("hour_index", as_index=False)["hourly_demand"].sum()

#         # Save result
#         output_file = os.path.join(output_folder, f"{province}_aggregated_hourly_demand.csv")
#         aggregated_df.to_csv(output_file, index=False)
#         print(f"Aggregated: {province}")

#     print(f"Aggregation complete. Results saved in: {output_folder}")
    merge_province_hourly_demand(output_folder, year)

# def merge_province_hourly_demand(input_folder, year, output_file="combined_hourly_demand.csv"):
#     """
#     Merges all province-level aggregated hourly demand CSVs into a single file.

#     Parameters:
#     - input_folder (str): Path to the folder containing province-level aggregated CSVs.
#     - output_file (str): Name or path of the output CSV file to save the merged data.
#     """
#     merged_df = None
#     name, ext = os.path.splitext(output_file)
#     output_file = f"{name}_{year}{ext}"

#     for filename in os.listdir(input_folder):
#         if filename.endswith("_aggregated_hourly_demand.csv"):
#             file_path = os.path.join(input_folder, filename)

#             # Extract province name from filename
#             province = filename.split("_")[0]

#             # Read CSV
#             df = pd.read_csv(file_path)

#             # Rename the hourly_demand column to the province name
#             df = df.rename(columns={"hourly_demand": province})

#             # Merge with existing DataFrame
#             if merged_df is None:
#                 merged_df = df
#             else:
#                 merged_df = pd.merge(merged_df, df, on="hour_index", how="outer")

#     if merged_df is not None:
#         merged_df = merged_df.sort_values("hour_index")
#         merged_df.to_csv(output_file, index=False)
#         print(f"Merged CSV saved to {output_file}")
#     else:
#         print("No matching CSV files found in the specified folder.")

#     # Define the start date corresponding to hour_index = 0
#     start_date = datetime(int(year), 1, 1, 0, 0)

#     # Read the input CSV
#     df = pd.read_csv(output_file)

#     # Convert hour_index to datetime
#     df["date"] = df["hour_index"].apply(lambda x: start_date + timedelta(hours=int(x)))

#     # Format the datetime as "M/D/YYYY H:MM" (e.g., 1/1/2020 0:00)
#     df["date"] = df["date"].dt.strftime("%-m/%-d/%Y %H:%M")

#     # Reorder columns: put datetime first, drop hour_index
#     cols = ["date"] + [col for col in df.columns if col not in ["date", "hour_index"]]
#     df = df[cols]
#     # Define the mapping of full names to short forms
#     rename_dict = {
#         'Alberta': 'AB',
#         'BritishColumbia': 'BC',
#         'Manitoba': 'MB',
#         'NewBrunswick': 'NB',
#         'NewfoundlandandLabrador': 'NL',
#         'NorthwestTerritories': 'NT',
#         'NovaScotia': 'NS',
#         'Nunavut': 'NU',
#         'Ontario': 'ON',
#         'PrinceEdwardIsland': 'PE',
#         'Quebec': 'QC',
#         'Saskatchewan': 'SK',
#         'Yukon': 'YT',
#         'Canada': 'CA', 
#     }

#     # Filter the dictionary to include only columns that are present in the DataFrame
#     valid_columns = {col: short for col, short in rename_dict.items() if col in df.columns}

#     # Rename only the valid columns
#     df = df.rename(columns=valid_columns)

#     output_file = "combined_hourly_demand_with_datetime.csv"
#     name, ext = os.path.splitext(output_file)
#     output_file = f"{name}_{year}{ext}"
#     # Save the updated DataFrame to a new CSV
#     df.to_csv(output_file, index=False)

#     print(f"Saved with datetime column to: {output_file}")
def merge_province_hourly_demand(input_folder, year, output_file="combined_hourly_demand.csv"):
    

    # Initialize dictionary to hold data by (province, sector)
    hourly_data = defaultdict(dict)
    target_sectors = {
        "FinalEnergy|Industry|Electricity",
        "FinalEnergy|ResidentialandCommercial|Electricity",
        "FinalEnergy|Transportation|Electricity"
    }

    for filename in os.listdir(input_folder):
        if not filename.endswith(".csv") or "_hourly_demand" not in filename:
            continue

        filepath = os.path.join(input_folder, filename)
        parts = filename.replace(".csv", "").split("_")
        province = parts[0]
        sector = parts[1]+'|'+parts[2]+'|'+parts[3] if len(parts) > 3 else None

        df = pd.read_csv(filepath)

        if sector in target_sectors:
            col_name = f"{province}_{sector}"
            df2 = df.rename(columns={"hourly_demand": col_name})
            df2 = df2[["hour_index", col_name]]  
            hourly_data[province][sector] = df2
        else:
            continue  # ignore unknown files

    all_merged = None

    for province, sector_dfs in hourly_data.items():
        merged = None

        for sector, df in sector_dfs.items():
            if merged is None:
                merged = df
            else:
                merged = pd.merge(merged, df, on="hour_index", how="outer")

        # Create total column for the province
        sector_cols = [f"{province}_{s}" for s in target_sectors if f"{province}_{s}" in merged.columns]
        merged[province] = merged[sector_cols].sum(axis=1)

        # Add to global merged df
        if all_merged is None:
            all_merged = merged
        else:
            all_merged = pd.merge(all_merged, merged, on="hour_index", how="outer")

    if all_merged is None:
        print("⚠️ No data to merge.")
        return

    start_date = datetime(int(year), 1, 1, 0, 0)
    all_merged["date"] = all_merged["hour_index"].apply(lambda x: start_date + timedelta(hours=int(x)))
    all_merged["date"] = all_merged["date"].dt.strftime("%-m/%-d/%Y %H:%M")

 
    cols = ["date"] + [col for col in all_merged.columns if col not in ["date", "hour_index"]]
    all_merged = all_merged[cols]

    # Rename province names if needed
    rename_dict = {
        'Alberta': 'AB',
        'BritishColumbia': 'BC',
        'Manitoba': 'MB',
        'NewBrunswick': 'NB',
        'NewfoundlandandLabrador': 'NL',
        'NorthwestTerritories': 'NT',
        'NovaScotia': 'NS',
        'Nunavut': 'NU',
        'Ontario': 'ON',
        'PrinceEdwardIsland': 'PE',
        'Quebec': 'QC',
        'Saskatchewan': 'SK',
        'Yukon': 'YT',
        'Canada': 'CA',
    }

    for full_name, short_code in rename_dict.items():
        all_merged.columns = [col.replace(full_name, short_code) for col in all_merged.columns]

    
    name, ext = os.path.splitext(output_file)
    output_file = f"{name}{ext}"
    all_merged.to_csv(output_file, index=False)
    print(f"Saved merged sectoral demand to: {output_file}")


def update_config_file(config_path, year, province):
    config = configparser.ConfigParser()
    config.read(config_path)

    
    if config.has_option('Commitment_Times', 'user_startdate'):
        _, m, d = config['Commitment_Times']['user_startdate'].split('/')
        config['Commitment_Times']['user_startdate'] = f"{year}/{m}/{d}"
    if config.has_option('Commitment_Times', 'user_enddate'):
        _, m, d = config['Commitment_Times']['user_enddate'].split('/')
        config['Commitment_Times']['user_enddate'] = f"{year}/{m}/{d}"

    # Update vre_year
    config['Run_Parameters']['vre_year'] = str(year)

    # Update provinces
    config['Linkage_Options']['provinces'] = province

    # Write back to file
    with open(config_path, 'w') as configfile:
        config.write(configfile)


def main():
    gridcell_data = pd.read_csv(Path(__file__).resolve().parent / "gridcells.csv").drop('Unnamed: 0', axis=1)
    merra_data = gridcell_data[['lon', 'lat', 'ba', 'pr', 'grid_cell']].copy()
    merra_data.rename(columns={'pr': 'Province'}, inplace=True)

    print("Fetching and processing generator data...")
    generators = load_generators_data()
    generators.to_csv('generators.csv', index=False)

    print("Analyzing generator type distribution...")
    #gets distribution of different hydro, oil and storage generators
    analyze_generator_distribution(generators)

    print("\nFetching and processing MESSAGEix data...")
    message_path = BASE_DIR / "MESSAGEix-CA_baseline_2025-03-17--11-11.xlsx"
    # message_path = BASE_DIR / "nz-dmd-reduction.xlsx"
    message_df = process_messageix_file(message_path)
    message_df.to_csv('message_final.csv', index=False)

    possible_provinces = [
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Nova Scotia",
    "Ontario",
    "Prince Edward Island",
    "Quebec",
    "Saskatchewan",
    "Northwest Territories",
    "Nunavut",
    "Yukon"]

    possible_years = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]

    selected_provinces = select_options(possible_provinces, "Select provinces to convert for generator disaggregation")                                
    selected_years = select_options(possible_years, "Select years to convert for generator disaggregation")
    selected_years = [int(year) for year in selected_years]

    generators_filtered = prepare_generators_for_merge(generators)
    generators_filtered.to_csv('generators_grouped.csv', index=False)
    all_disaggregated_results = pd.DataFrame()
    print(selected_provinces, selected_years)
    
    for province in selected_provinces:
        for year in selected_years:
            print(f"\nProcessing province: {province}, year: {year}")

            generate_hourly_demand_profiles(message_path, int(year))

            print("Comparing MESSAGEix vs CODERS capacities...")
            # message_df_filtered = message_df[(message_df['Region'].str.lower() == province.lower()) &
            #                              (message_df['year'] == year)]
            message_df_filtered = message_df[['gen_type_coders', 'Region', year]].copy()
            message_df_filtered = message_df_filtered[message_df_filtered['Region'].str.lower() == province.lower().replace(" ", "")]

            # generators_filtered_prov = generators_filtered[generators_filtered['operating_region'].str.lower() == province.lower()]
            generators_filtered['operating_region'] = generators_filtered['operating_region'].str.strip().str.lower().str.replace(" ", "")
            generators_filtered_prov = generators_filtered[generators_filtered['operating_region'] == province.lower().replace(" ", "")]

            generators_necessary = compare_message_and_coders(message_df_filtered, generators_filtered_prov, year)
            generators_necessary.to_csv(f'generators_necessary_{province}_{year}.csv', index=False)

            message_vre_generators = get_wind_and_solar_capacity(generators_necessary, year)

            print("\nMerged capacity comparison:")
            print(generators_necessary)

            generators_necessary.rename(columns={'Region': 'province'}, inplace=True)
            avg_gen_size_canada = generators.groupby('gen_type_copper')['unit_installed_capacity'].mean()
            

            existing_generators = generators[(generators['operating_region'].str.lower() == province.lower())].reset_index(drop=True)

            if not message_vre_generators.empty:
                new_vre_generators = message_vre_generators[(message_vre_generators['province'] == province.lower())
                                                        & (message_vre_generators['year'] <= year)].reset_index(drop=True)
                # new_vre_generators = message_vre_generators[(message_vre_generators['province'] == province.lower())].reset_index(drop=True)
                new_vre_generators = new_vre_generators.drop('year', axis=1)
                new_vre_generators = new_vre_generators.groupby(['grid_cell', 'lon', 'lat', 'province']).sum().reset_index()
            else:
                new_vre_generators = message_vre_generators
            # new_generators = generators_necessary[generators_necessary['province'] == province]
            new_generators = generators_necessary[generators_necessary['province'].str.lower().str.replace(' ', '') == province.lower().replace(' ', '')]

            vre_gen_types = ["wind_ons", "wind_ons_recon", "wind_onshore", "wind_ofs", "wind_ofs_recon", "wind_offshore", "wind", "solar", "solar_recon"]
            min_gen_size =400

            if not new_vre_generators.empty:
                existing_generators = add_vre_generators(existing_generators, new_vre_generators, avg_gen_size_canada)
            existing_generators = add_new_message_generators(existing_generators, new_generators, avg_gen_size_canada, 
                                                                                        vre_gen_types, min_gen_size)
            if existing_generators['generation_unit_code'].str.contains('need_to_build').any():
                print(f"WARNING: disaggregation of generators in {province},{year} has resulted in generators that may need to be manually assigned locations")

            print(existing_generators[['gen_type_copper', 'unit_installed_capacity']].groupby('gen_type_copper').sum())
            windcf = pd.read_csv(Path(__file__).resolve().parent / "windcf.csv")
            solarcf = pd.read_csv(Path(__file__).resolve().parent / "solarcf.csv")
            scenario_disaggregated_results = format_iamc(existing_generators, solarcf.copy(), windcf.copy(), 
                                                                                    merra_data, province,year)
            all_disaggregated_results = pd.concat([all_disaggregated_results, scenario_disaggregated_results])
            
    all_disaggregated_results.to_csv('total_output_summary.csv', index=False)

    silver_script_dir = r"C:\Users\bipas\Downloads\linkage\silver\src\SILVER_Code" # Adjust this path as needed to silver code
    config_path = r"C:\Users\bipas\Downloads\linkage\silver\src\SILVER_Data\user_inputs\linkage\configVariables.ini" # Adjust this path as needed to configVariables of the scenario
    silver_script = os.path.join(silver_script_dir, "SILVER_Runner.py")
    rename_dict = {
    'Alberta': 'AB',
    'BritishColumbia': 'BC',
    'Manitoba': 'MB',
    'NewBrunswick': 'NB',
    'NewfoundlandandLabrador': 'NL',
    'NorthwestTerritories': 'NT',
    'NovaScotia': 'NS',
    'Nunavut': 'NU',
    'Ontario': 'ON',
    'PrinceEdwardIsland': 'PE',
    'Quebec': 'QC',
    'Saskatchewan': 'SK',
    'Yukon': 'YT',
    'Canada': 'CA',
}
    selected_provinces = [rename_dict.get(p.replace(" ", ""), p) for p in selected_provinces]
    for province in selected_provinces:
        for year in selected_years:
            print(f"Updating config for {province}, {year}")
            update_config_file(config_path, year, province)
            print(f"Running SILVER_Runner for {province}, {year}") #make sure silver locally is set to linkage branch and linkage scenario with the correct config exists 
            subprocess.run(
                ["python", silver_script, "-sc", "linkage"],
                cwd=silver_script_dir,  
                check=True
            )


if __name__ == "__main__":
    main()
