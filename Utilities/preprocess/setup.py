import toml
import message_ix
import ixmp
import pandas as pd
from ixmp import Scenario
from pathlib import Path

from Utilities.preprocess.process_historical_activity import update_historical_activity


def setup_scenario(scenario_name: str):
    config_path = Path(f"scenarios/{scenario_name}/config.toml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist at {config_path}")
    
    config = toml.load(config_path)

    modelName = config['general']['model_name']
    scenarioName = config['general']['scenario_name']
    platform_name = config['general']['ix_platform']
    version = config['general']['version']
    annotation = config['general']['annotation']
    process_historical = config['pre_process']['process_historical_data']
    add_hydrogen_shares = config['pre_process']['add_hydrogen_shares']
    use_reporter = config['post_process']['generate_reporter_output']
    ssp = 'SSP2'  

    mp = ixmp.Platform(name=platform_name)
    msg = message_ix.Scenario(mp, modelName, scenarioName, version='new', annotation=annotation)

    excel_path = Path(config['data']['provincial_input_file'])
    msg.read_excel(excel_path, add_units=True, commit_steps=False, init_items=True)

    if process_historical:
        scenario_folder = config['data']['scenario_folder']
        update_historical_activity(msg, scenario_folder)
    
    if add_hydrogen_shares:
        add_hydrogen_shares(msg, scenario_folder)

    caseName = msg.model + '__' + msg.scenario + '__v' + str(msg.version)
    
    # msg.solve()

    return mp, msg


