import pandas as pd
import numpy as np
from pathlib import Path
from model.utilities.preprocess.process_demands import adjust_demands

def update_historical_activity(scenario, path):
    """
    Update the historical activity parameter in the scenario with data from a specified path.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        path (str or Path): Path to the the historical activity data.
    """
    # Checkout scenario for editing
    scenario.check_out() 
    ha = scenario.par('historical_activity')
    # Read historical activity data from the folder specified in config.toml
    ha_new = pd.read_csv(Path(f"{path}/historical_activity.csv"))
    ha_new = balance_import_export(ha_new)
    # Remove the previous historical_activity from the scenario
    scenario.remove_par('historical_activity', ha)
    # Add new historical activity data to the scenario
    scenario.add_par('historical_activity', ha_new)
    scenario.commit('Updated historical activity based on new data')
    adjust_demands(scenario)
    





def balance_import_export(historical_activity):
    PROVINCES = ["Alberta", "BritishColumbia", "Manitoba", "Ontario", "NewBrunswick",
             "NewfoundlandandLabrador", "NovaScotia", "PrinceEdwardIsland", "Quebec", "Saskatchewan", "Yukon"]

    # Define the technologies
    foil_techs = ['foil_fs', 'foil_i', 'foil_ppl', 'foil_rc', 'foil_t_d', 'foil_trp']
    loil_techs = ['loil_fs', 'loil_i', 'loil_ppl', 'loil_rc', 'loil_t_d', 'loil_trp']
    gas_techs = ['gas_cc', 'gas_ct', 'gas_fs', 'gas_i', 'gas_ppl', 'gas_rc', 'gas_t_d', 'gas_trp']
    coal_techs = ['coal_fs', 'coal_i', 'coal_ppl', 'coal_rc', 'coal_t_d', 'coal_trp']
    def sum_demand(df, techs):
        return df[df['technology'].isin(techs)].groupby(['year_act', 'node_loc'])['value'].sum()

    years = historical_activity['year_act'].unique()
    
    for year in years:
        df_year = historical_activity[(historical_activity['year_act'] == year) & (historical_activity['node_loc'].isin(PROVINCES))]
        
        coal_demand = sum_demand(df_year, coal_techs)
        foil_demand = sum_demand(df_year, foil_techs)
        loil_demand = sum_demand(df_year, loil_techs)
        gas_demand = sum_demand(df_year, gas_techs)
        oil_demand = foil_demand.add(loil_demand, fill_value=0)

        pivot_df = df_year.pivot_table(index='node_loc', columns='technology', values='value', aggfunc='sum').reset_index()

        required_columns = ['coal_extr_mpen', 'coal_imp', 'coal_exp', 'gas_extr_mpen', 'gas_imp', 'gas_exp', 'oil_extr_mpen',
                            'oil_imp', 'oil_exp']
        for tech in required_columns:
            if tech not in pivot_df.columns:
                pivot_df[tech] = 0

        production_import_export_data = pivot_df[['node_loc'] + required_columns].fillna(0)

        demand_data = pd.DataFrame({
            'node_loc': coal_demand.index.get_level_values('node_loc'),
            'coal_demand': coal_demand.values,
            'gas_demand': gas_demand.values,
            'oil_demand': oil_demand.values
        }).fillna(0)

        merged_df = production_import_export_data.merge(demand_data, on='node_loc', how='left').fillna(0)

        def balance_energy(row, prod_col, imp_col, exp_col, demand_col):
            production = row[prod_col]
            imports = row[imp_col]
            exports = row[exp_col]
            demand = row[demand_col]

            net_balance = production + imports - exports

            if net_balance < demand:
                imports += demand - net_balance
            elif net_balance > demand:
                exports += net_balance - demand

            if imports < 0:
                exports += abs(imports)
                imports = 0
            

            row[imp_col] = imports
            row[exp_col] = exports
            return row

        balanced_df = merged_df.copy()

        balanced_df = balanced_df.apply(
            balance_energy, axis=1,
            prod_col='coal_extr_mpen', imp_col='coal_imp', exp_col='coal_exp', demand_col='coal_demand'
        )

        balanced_df = balanced_df.apply(
            balance_energy, axis=1,
            prod_col='gas_extr_mpen', imp_col='gas_imp', exp_col='gas_exp', demand_col='gas_demand'
        )

        balanced_df = balanced_df.apply(
            balance_energy, axis=1,
            prod_col='oil_extr_mpen', imp_col='oil_imp', exp_col='oil_exp', demand_col='oil_demand'
        )

        for index, row in balanced_df.iterrows():
            historical_activity.loc[
                (historical_activity['year_act'] == year) & 
                (historical_activity['node_loc'] == row['node_loc']) & 
                (historical_activity['technology'] == 'coal_imp'), 'value'] = row['coal_imp']
            historical_activity.loc[
                (historical_activity['year_act'] == year) & 
                (historical_activity['node_loc'] == row['node_loc']) & 
                (historical_activity['technology'] == 'coal_exp'), 'value'] = row['coal_exp']
            historical_activity.loc[
                (historical_activity['year_act'] == year) & 
                (historical_activity['node_loc'] == row['node_loc']) & 
                (historical_activity['technology'] == 'gas_imp'), 'value'] = row['gas_imp']
            historical_activity.loc[
                (historical_activity['year_act'] == year) & 
                (historical_activity['node_loc'] == row['node_loc']) & 
                (historical_activity['technology'] == 'gas_exp'), 'value'] = row['gas_exp']
            historical_activity.loc[
                (historical_activity['year_act'] == year) & 
                (historical_activity['node_loc'] == row['node_loc']) & 
                (historical_activity['technology'] == 'oil_imp'), 'value'] = row['oil_imp']
            historical_activity.loc[
                (historical_activity['year_act'] == year) & 
                (historical_activity['node_loc'] == row['node_loc']) & 
                (historical_activity['technology'] == 'oil_exp'), 'value'] = row['oil_exp']

    return historical_activity

# Example usage:
# updated_historical_activity = balance_import_export(historical_activity_df)
