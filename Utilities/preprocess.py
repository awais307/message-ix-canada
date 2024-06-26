import pandas as pd

def update_historical_activity(scenario, path):
    scenario.check_out()  # Starts modifications on the scenario

    # Reading current historical activity data from the scenario
    df = scenario.par('historical_activity')

    # Loading new data from Excel
    df_new = pd.read_excel(path, sheet_name='historical_activity')

    # Assuming these functions are defined and they modify df_new directly
    balance_import_export(df_new)
    update_demands(df_new)

    # Removing old data and adding updated data
    scenario.remove_par('historical_activity', df)
    scenario.add_par('historical_activity', df_new)

    # Committing the changes with a description
    scenario.commit('Updated historical activity based on new data')
