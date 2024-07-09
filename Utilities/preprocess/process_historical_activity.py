import pandas as pd
import numpy as np
from pathlib import Path

def update_historical_activity(scenario, path):
    """
    Update the historical activity parameter in the scenario with data from a specified path.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        path (str or Path): Path to the the historical activity data.
    """
    scenario.check_out() 
    df = scenario.par('historical_activity')
    df_new = pd.read_csv(Path(f"{path}/historical_activity.csv"))
    #print(df_new)
    scenario.remove_par('historical_activity', df)
    scenario.add_par('historical_activity', df_new)
    scenario.commit('Updated historical activity based on new data')
