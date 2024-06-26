import toml
import message_ix
import ixmp
import pandas as pd
from ixmp import Scenario
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent))

from Utilities.preprocess import update_historical_activity

# Check for command line argument
if len(sys.argv) != 2:
    print("Usage: python Message-CANADA.py <scenario_folder>")
    sys.exit(1)

scenario_folder = sys.argv[1]

# Load configuration settings from the specified scenario folder
config_path = Path(f"scenarios/{scenario_folder}/config.toml")
if not config_path.exists():
    print(f"Error: Config file does not exist at {config_path}")
    sys.exit(1)
config = toml.load(config_path)

# Assign variables from the config file
modelName = config['general']['model_name']
scenarioName = config['general']['scenario_name']
platform_name = config['general']['ix_platform']
version = config['general']['version']
annotation = config['general']['annotation']
process_historical = config['pre_process']['process_historical_data']
ssp = 'SSP2'  

# Initialize the platform and scenario
mp = ixmp.Platform(name=platform_name)
msg = message_ix.Scenario(mp, modelName, scenarioName, version='new', annotation=annotation)

# Read the Excel file as specified in the config
excel_path = Path(config['data']['provincial_input_file'])
msg.read_excel(excel_path, add_units=True, commit_steps=False, init_items=True)

# Optional: Process historical data
if process_historical:
    scenario_folder = config['data']['scenario_folder']
    update_historical_activity(msg, scenario_folder)

msg.solve()
