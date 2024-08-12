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
        df = pd.read_excel(path /'hydrogen_shares.xlsx', sheet_name=sheet_name)
        print(f"Sheet name: {sheet_name}")
        if sheet_name in scenario.set_list():
            if sheet_name == 'cat_tec':
                continue
            print('sets',sheet_name)
            if sheet_name in (['type_tec','shares']):
                scenario.add_set(sheet_name, df[sheet_name])
            else:
                scenario.add_set(sheet_name, df)

        elif sheet_name in scenario.par_list():
            scenario.add_par(sheet_name, df)
            print('par',sheet_name)

    print(scenario.par("share_commodity_lo")['shares'].unique())


    df = scenario.par('relation_activity')
    scenario.remove_par('relation_activity', df)
    relation_h2 = ['UE_industry_sp_fc', 'UE_res_comm_sp_fc', 'UE_industry_th_hydrogen','UE_res_comm_th_hydrogen']
    df_relation = df[~df['relation'].isin(relation_h2)]
    scenario.add_par('relation_activity',df_relation )


    scenario.commit('Updated shares based on new data')
