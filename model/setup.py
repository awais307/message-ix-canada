import toml
import message_ix
import ixmp
import pandas as pd
from pathlib import Path

from model.utilities.preprocess.process_historical_activity import update_historical_activity
from model.policies.add_hydrogen_shares import add_hydrogen_shares
from model.utilities.postprocess.reporter import generate_report


def setup_scenario(scenario_name: str):
    """
    Set up and initialize a MESSAGEix scenario based on the provided configuration.

    This function reads a configuration file for a given scenario, initializes a
    MESSAGEix scenario object, and performs pre-processing steps as defined in the
    configuration. The function returns the platform and scenario objects for further use.

    Args:
        scenario_name (str): The name of the scenario to set up.

    Returns:
        tuple: A tuple containing the ixmp.Platform object and the message_ix.Scenario object.

    Raises:
        FileNotFoundError: If the configuration file for the scenario does not exist.
    """
    
    config_path = Path(f"../scenarios/{scenario_name}/config.toml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist at {config_path}")
    
    config = toml.load(config_path)

    modelName = config['general']['model_name']
    scenarioName = config['general']['scenario_name']
    platform_name = config['general']['ix_platform']
    version = config['general']['version']
    annotation = config['general']['annotation']
    process_historical = config['pre_process']['process_historical_data']
    add_hydrogen_shares_f = config['pre_process']['add_hydrogen_shares']
    use_reporter = config['post_process']['generate_reporter_output']
    solve = config['model']['solve']
    to_excel = config['post_process']['export_to_xlsx']
    #TODO add option for SSP
    # ssp = 'SSP2' 
    
    mp = ixmp.Platform(name=platform_name)
    scenario = message_ix.Scenario(mp, modelName, scenarioName, version= version, annotation=annotation)
    
    caseName = scenario.model + '__' + scenario.scenario + '__v' + str(scenario.version)
    
    script_dir = Path(__file__).resolve().parent
    excel_path = script_dir / config['data']['provincial_input_file']
    scenario.read_excel(excel_path, add_units=True, commit_steps=False, init_items=True)

    if process_historical:
        scenario_folder = script_dir / config['data']['scenario_folder']
        update_historical_activity(scenario, scenario_folder)
    
    if add_hydrogen_shares_f:
        scenario_folder = config['data']['scenario_folder']
        path_to_hydrogen_data = script_dir / scenario_folder
        add_hydrogen_shares(scenario, path_to_hydrogen_data)

    
    
    if solve:
        scenario.solve(solve_options={'barcrossalg': '2','lpmethod':'1'}, case=caseName)
        if use_reporter:
            generate_report(scenario, output_path=f'{caseName}.csv', min_year=2020, max_year=2060, from_excel=False, unit_correct=True)

    if to_excel:
        scenario.to_excel(f'{caseName}.xlsx')

    # msg.solve()

    return mp, scenario







