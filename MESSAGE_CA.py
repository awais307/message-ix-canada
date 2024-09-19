#### MESSAGE_IX CANADA ####

#--- Main script for executing the model ---#

'''
This script will contain the main workflow of the model. 
It should only contain the main steps for model execution, while all the function and class declarations
should be housed in dedicated scripts, which are subsequentially imported here.

----------------

# Project references:



----------------

# Project authors:


'''

#####################################################

import os
from pathlib import Path
from setuptools import setup, find_packages
import sys
sys.path.append(str(Path(__file__).resolve().parent))

from model.message_phases import (MESSAGE_CA, Plotter_MSG)

# Set up the packages
'''
setup(
    name='MESSAGE_CANADA',
    packages=find_packages(),
)

if len(sys.argv) != 2:
    print("Usage: python Message-CANADA.py <scenario_folder>")
    sys.exit(1)
'''
scenario_folder = 'baseline' #sys.argv[1]

# Create model instance
msg1 = MESSAGE_CA(scenario_name=scenario_folder)

# Set up model with the selected scenario
platform, msg_scenario, msg_folder = msg1.setup_scenario()

# Plotter

msg_plt = Plotter_MSG(msg_scenario)
nodes = msg_scenario.set('node')[2:]
msg_plt.plotter(case="test",nodeloc="Alberta",path="./",yr_min=2020, yr_max=2060)


# Remove the model solution (if any) and check out the scenario
try:
    msg_scenario.remove_solution()
except ValueError as e:
    print(e)
msg_scenario.check_out()

#config_path = Path(f"scenarios/{scenario_folder}/config.toml")

