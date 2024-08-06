import pandas as pd
import numpy as np
from pathlib import Path

def add_hydrogen_shares(scenario, path):
    """

    Add hydrogen shares to a MESSAGEix scenario.

    This function modifies the provided MESSAGEix scenario to include hydrogen shares. 
    The specific implementation details, such as the hydrogen share percentages and the affected sectors, 
    should be added within this function.

    Args:
        scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the hydrogen shares will be added.

    Returns:
        None

    """

    scenario.check_out() 
    
    path=Path(path)
    data = pd.ExcelFile(path / 'hydrogen_shares.xlsx')

    # Loop through each sheet
    for sheet_name in data.sheet_names:
        # Perform operations on the DataFrame
        df = pd.read_excel(path /'hydrogen_shares_V2.xlsx', sheet_name=sheet_name)
        print(f"Sheet name: {sheet_name}")
        if sheet_name in msg.set_list():
            if sheet_name == 'cat_tec':
                continue
            print('sets',sheet_name)
            if sheet_name in (['type_tec','shares']):
                msg.add_set(sheet_name, df[sheet_name])
            else:
                msg.add_set(sheet_name, df)

        elif sheet_name in msg.par_list():
            msg.add_par(sheet_name, df)
            print('par',sheet_name)

    msg.commit('Updated historical activity based on new data')

    print(msg.par("share_commodity_lo")['shares'].unique())

    #print(scenario.par("share_commodity_lo")['shares'].unique())