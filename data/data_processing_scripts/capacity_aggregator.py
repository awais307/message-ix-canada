import pandas as pd
import os
import time
import argparse
import warnings
from phases.preprocessingtools import *
import toml
from tools.COPPER_Cost import *
from tools.COPPER_tools import (init_input, get_VRE_cf, dataframe_processor, hour_mapper, pyomo_parameter)
from phases.preprocess_validation import pre_process_copper
#from utils.constraints.costs_constraints import *

import requests
import csv
def save_csv(data, csv_filename):
    # Write the array to a CSV file (each element in a separate row)
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        
        # Write each element as a new row
        for item in data:
            writer.writerow([item])

def is_offshore_marine_regions(lat, lon):
    url = f"https://geogratis.gc.ca/services/elevation/cdem/altitude?lat={lat}&lon={lon}"
    response = requests.get(url).json()
    
    if response['altitude']:
        return "Onshore" 
    else:
        return "Offshore"

# Test for a point in the ocean
lat = 50.808230
lon = -59.019534
print(is_offshore_marine_regions(lat, lon))
#lat 45.36055529627886
#lon -80.7






warnings.filterwarnings("error")

########################################################
#####   COMMAND LINE ARGUMENTS AND INPUT FORMATTING ####
########################################################

# Command line arguments
arguments = argparse.ArgumentParser()
arguments.add_argument("-sc", "--scenario", dest="scenario", default="BAU_scenario", type=str,
                       help="Select the COPPER scenario")
#other valid options include glpk and cbc
arguments.add_argument("-so", "--solver", dest="solver", default="cplex", type=str,
                       help="Select the COPPER solver")
arguments.add_argument("-o", "--output", dest="output", default=os.path.join(os.getcwd(), 'results'), #type=Path,
                       help="Select the Output folder")
arguments.add_argument("-t", "--test",  action='store_true', dest="test",
                       help="Choose if COPPER is running on test mode, or as a full scenario run")
arguments.add_argument("-se", "--seed", dest="seed", default=None, type=int,
                       help="Set a seed to make results reproducible (only works with solver=glpk")
arguments.add_argument("-cv", "--cap_values", dest="gen_cap_values", action="store_true",
    help="Generate COPPER parameters using pre-process functions. Can generate run days, and capacity values")
# More options (i.e subarguments) need to be explored for the run day generation
arguments.add_argument("-rd", "--rep_day", dest="rep_days_check", action='store_true',
                       help="Create new representative days for your config file using your demand file")
arguments.add_argument("-c", '--concise', dest='concise', default=False, action='store_true',
                       help="Concise results saves a single output csv file and deletes all other outputs")
arguments.add_argument("-te", "--tee", dest="solver_log", default=False, action="store_true", 
                       help="Display solver log while solving problem")

args = arguments.parse_args()

########################################################

# Check if scenario came from command line
scenario = args.scenario
solver = args.solver
solver_log = args.solver_log
destination_folder = args.output
test_flag = True #args.test
concise_flag = args.concise
rep_days_check = args.rep_days_check
cv_gen = args.gen_cap_values 
seed = args.seed
seed_message = f'* Using Custom seed {seed}\n' if seed is not None else '* Using Randomized Seed\n'
print("\n==================================================\n" +
      "Running COPPER using the following set-up:\n" +
      f"* Scenario: {scenario}\n" +
      f"* Solver: {solver}, solver log display is set to {solver_log}\n" + 
      f"* Output folder: {destination_folder}\n" +
      f"* Test mode: {test_flag}\n" +
      f'* Concise outputs: {concise_flag}\n' +
      seed_message +
      "==================================================\n")

if test_flag:
    test = True
else:
    test = False

# Load config file
#config = toml.load('config.toml')

# Initializing all sets
### All regions
ap= [
        "British Columbia",
        "Alberta",
        "Saskatchewan",
        "Manitoba",
        "Ontario",
        "Quebec",
        "New Brunswick",
        "Newfoundland and Labrador",
        "Nova Scotia",
        "Prince Edward Island",
    ]

aba= [
        "British Columbia.a",
        "Alberta.a",
        "Saskatchewan.a",
        "Manitoba.a",
        "Ontario.a",
        "Ontario.b",
        "Quebec.a",
        "Quebec.b",
        "New Brunswick.a",
        "Newfoundland and Labrador.a",
        "Newfoundland and Labrador.b",
        "Nova Scotia.a",
        "Prince Edward Island.a",
    ]  # all possible balancing areas

pds= ["2025","2030","2035","2040","2045","2050"]

#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#

######### Model Pre-processing ##########

#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#/#

preprocess_start = time.time()
input_process = pre_process_copper(scenario)
get_file = init_input(scenario)

##### Reading hydro units capacity factor data
# hydrocf = dataframe_processor(pd.read_csv(get_file('hydro_cf.csv')), ap, prov_idx=0)
# hydro_cf = dict(hydrocf.values)

#cf_dict
### Reading extant wind and solar data
# generators_df = pd.read_csv(get_file('generators.csv'))
# generators_df = generators_df[generators_df['gen_type_copper'].isin(['solar','wind_ons'])] 
# generators_dict = generators_df.to_dict()

# extantwindsolar = pd.read_csv(get_file('extant_wind_solar.csv'))
# extant_wind_solar_raw = extantwindsolar.copy()

# extant_wind_solar = {}
# for PD in pds:
#     extant_wind_solar[PD] = dict(extantwindsolar[['location', f'{PD}']].values)

# #aggregates the capacity of existing vre by province and vre type
# extantwindsolar = extantwindsolar.reset_index(drop=True)
# extantwindsolar[["gl", "type"]] = extantwindsolar["location"].str.split(".", expand=True)
# extantwindsolar["gl"] = extantwindsolar["gl"].astype(int)
# extantwindsolar["aba"] = extantwindsolar["gl"].apply(map_gl_to_ba.get)

gridcell_data = dataframe_processor(pd.read_csv(get_file('gridcells.csv')), ap, prov_idx=4)

area_per_grid_cell = {}
area_per_grid_cell['wind_ons'] = { gridcell_data['grid_cell'][index]: gridcell_data['surface_area_ons'][index]/2476.21 for index in range(len(gridcell_data['grid_cell']))}
area_per_grid_cell['wind_ofs'] = { gridcell_data['grid_cell'][index]: gridcell_data['surface_area_ofs'][index]/2476.21 for index in range(len(gridcell_data['grid_cell']))}


map_gl_to_ba = dict(gridcell_data[['grid_cell', 'ba']].values)  # map grid locations to balancing areas
map_gl_to_pr = dict(gridcell_data[['grid_cell', 'pr']].values)  # map grid locations to provinces


h = list(range(1, 8761))
hours = len(h)

gen = ['solar', 'wind_ons', 'wind_ofs']

levels = {
    'wind_ofs':['c1', 'c2', 'c3', 'c4+'],
    'wind_ons':['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8+'],
    'solar':['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7+']
}
sums = {AP:{GEN: {level:0 for level in levels[GEN]} for GEN in gen} for AP in ap}

gl = [str(GL) for GL in gridcell_data['grid_cell']]
new_gl_data = False
if new_gl_data:
    gl_offshore = [str(gridcell_data['grid_cell'][index]) for index in range(len(gridcell_data['grid_cell'])) if is_offshore_marine_regions(gridcell_data['lat'][index], gridcell_data['lon'][index]) == "Offshore"]
    gl_onshore = [str(GL) for GL in gridcell_data['grid_cell'] if str(GL)not in gl_offshore]
    save_csv(gl_offshore, 'gl_offshore.csv')
    save_csv(gl_onshore, 'gl_onshore.csv')
else:
    gl_offshore = pd.read_csv('gl_offshore.csv', header=None).squeeze().tolist()
    gl_onshore = pd.read_csv('gl_onshore.csv', header=None).squeeze().tolist()

[windcf_df, meanwincf, meanwincf_reduced] = get_VRE_cf(h, 'windcf.csv', get_file)
[solarcf_df, meansolarcf, meansolarcf_reduced] = get_VRE_cf(h, 'solarcf.csv', get_file)

cf_dict = {}
cf_dict['wind_ons'] = {GL:sum(windcf_df[int(GL)])/hours*area_per_grid_cell['wind_ons'][int(GL)] for GL in gl}
cf_dict['wind_ofs'] = {GL:sum(windcf_df[int(GL)])/hours*area_per_grid_cell['wind_ofs'][int(GL)] for GL in gl}
cf_dict['solar'] = {GL:sum(solarcf_df[int(GL)])/hours for GL in gl}

def factor_to_level(cf, GEN):
    if GEN == "wind_ons":
        if cf < 0.17:
            return 'c1'
        elif cf < 0.20:
            return 'c2'
        elif cf <  0.25:
            return 'c3'
        elif cf < 0.28:
            return 'c4'
        elif cf < 0.32:
            return 'c5'
        elif cf <  0.35:
            return 'c6'
        elif cf < 0.39:
            return 'c7'
        else:
            return 'c8+'
        
    if GEN == "wind_ofs":
        if cf < 0.28:
            return 'c1'
        elif cf < 0.32:
            return 'c2'
        elif cf <  0.35:
            return 'c3'
        else:
            return 'c4+'
        
    if GEN == "solar":
        if cf < 0.17:
            return 'c1'
        elif cf < 0.20:
            return 'c2'
        elif cf <  0.25:
            return 'c3'
        elif cf < 0.3:
            return 'c4'
        elif cf < 0.4:
            return 'c5'
        elif cf <  0.45:
            return 'c6'
        else:
            return 'c7+'
        
#for index, row in generators_df.iterrows(): #use capacity factor per grid df
for GEN in gen:
    for GL, CF in cf_dict[GEN].items():

        province = map_gl_to_pr[int(GL)]

        if GEN in ['wind_ons', 'wind_ofs']:
            capacity = CF * 2.5 * 2.47621 # constant for wind_ons and wind_ofs
        else:
            capacity = CF * 29.8 * 2.47621 # constant for solar

        level = factor_to_level(CF, GEN)

        sums[province][GEN][level] += (capacity)

# for PD in ['2025']:
#     for GEN in ['solar']:
#         for GL in [key.split('.')[0] for key in list(extant_wind_solar[PD].keys()) if GEN in key]:
#             if map_gl_to_pr[int(GL)] == "British Columbia":
#                 level = factor_to_level(cf_dict[GEN][GL], GEN)
#                 sums[PD][map_gl_to_pr[int(GL)]][GEN][level] += (extant_wind_solar[PD][f'{GL}.{GEN}']/1000)

wind_ons_levels_df = {level: [sums[AP]["wind_ons"][level] for AP in ap] for level in levels['wind_ons']}
wind_ons_levels_df = pd.DataFrame(wind_ons_levels_df)
wind_ons_levels_df.index = [f"{AP}"for AP in ap]  # Assign custom row index
wind_ons_levels_df = wind_ons_levels_df.reset_index()
wind_ons_levels_df = wind_ons_levels_df.reset_index().rename(columns={"index": "ISO"})
wind_ons_levels_df = wind_ons_levels_df.drop(columns=["level_0"])

wind_ofs_levels_df = {level: [sums[AP]["wind_ofs"][level] for AP in ap] for level in levels['wind_ofs']}
wind_ofs_levels_df = pd.DataFrame(wind_ofs_levels_df)
wind_ofs_levels_df.index = [f"{AP}"for AP in ap]  # Assign custom row index
wind_ofs_levels_df = wind_ofs_levels_df.reset_index()
wind_ofs_levels_df = wind_ofs_levels_df.reset_index().rename(columns={"index": "ISO"})
wind_ofs_levels_df = wind_ofs_levels_df.drop(columns=["level_0"])

solar_levels_df = {level: [sums[AP]["solar"][level] for AP in ap] for level in levels['solar']}
solar_levels_df = pd.DataFrame(solar_levels_df)
solar_levels_df.index = [f"{AP}"for AP in ap]  # Assign custom row index
solar_levels_df = solar_levels_df.reset_index()
solar_levels_df = solar_levels_df.reset_index().rename(columns={"index": "ISO"})
solar_levels_df = solar_levels_df.drop(columns=["level_0"])

df_dict = {
    "solar": solar_levels_df,
    "wind_ons": wind_ons_levels_df,
    "wind_ofs": wind_ofs_levels_df
}

with pd.ExcelWriter("VRE_Input_final.xlsx", engine="xlsxwriter") as writer:
    for sheet_name, df in df_dict.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)
