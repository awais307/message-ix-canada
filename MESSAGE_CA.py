import toml
import message_ix
import ixmp
import pandas as pd
from ixmp import Scenario
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent))

from model.message_phases import message_set_up


if len(sys.argv) != 2:
    print("Usage: python Message-CANADA.py <scenario_folder>")
    sys.exit(1)

scenario_folder = sys.argv[1]

# Create model instance
msg1 = message_set_up(scenario=scenario_folder)

# Validate config file
msg1.config_validation()

# Set up model with the selected scenario
mp1, msg_scenario, msg_folder = msg1.setup_scenario()

#config_path = Path(f"scenarios/{scenario_folder}/config.toml")

