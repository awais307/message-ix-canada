"""

"""

import pandas as pd
import numpy as np
from pathlib import Path
from message_ix_models import Context


def apply_renewable_potential(model_obj):
    """
    Args:
        scenario (MESSAGEix.Scenario):

    Returns:
        None
    """
    #renewable_potential_input_df = pd.read_csv(model_obj.ctx.path['renewable_potential'])
    renewable_potential_input_solar_df = pd.read_excel("./data/VRE_Input.xlsx", sheet_name="solar")
    renewable_potential_input_wind_ons_df = pd.read_excel("./data/VRE_Input.xlsx", sheet_name="wind_ons")

    input_format_msg_format_to_provinces = {element:element.replace(' ','') for element in renewable_potential_input_solar_df['ISO']}
    provinces = [element.replace(' ','') for element in renewable_potential_input_solar_df['ISO']]

    wind_ons_bins = [ element.replace('+','') for element in renewable_potential_input_wind_ons_df.columns if element != 'ISO']
    cols = [ element.replace('+','') for element in renewable_potential_input_wind_ons_df.columns]
    renewable_potential_input_wind_ons_dict = {
        input_format_msg_format_to_provinces[Province]: {bin:row[cols.index(bin)+1] for bin in wind_ons_bins for row in renewable_potential_input_wind_ons_df[renewable_potential_input_wind_ons_df['ISO']==Province].itertuples()} for Province in renewable_potential_input_wind_ons_df['ISO'].unique()
    }

    solar_bins = [ element.replace('+','') for element in renewable_potential_input_solar_df.columns if element != 'ISO']
    cols = cols = [ element.replace('+','') for element in renewable_potential_input_solar_df.columns]
    renewable_potential_input_solar_dict = {
        input_format_msg_format_to_provinces[Province]: {bin:row[cols.index(bin)+1] for bin in solar_bins for row in renewable_potential_input_solar_df[renewable_potential_input_solar_df['ISO']==Province].itertuples()} for Province in renewable_potential_input_solar_df['ISO'].unique()
    }

    renewable_potential_par_df = model_obj.ctx.source_scenario['scenario'].par('renewable_potential')

    rows_to_add = []
    rows_to_drop = [] # Store indexes to drop rows with extra bins than needed
    for index, row in renewable_potential_par_df.iterrows():
        tech = row['commodity']
        year = row['year']
        bin = row['grade']
        province = row['node']

        if tech == 'wind_onshore' and province in provinces:
            if bin in wind_ons_bins:
                new_val = renewable_potential_input_wind_ons_dict[province][bin]
                renewable_potential_par_df.loc[index, 'value'] = new_val
            else:
                rows_to_drop.append(index)
        elif tech == 'wind_onshore' and province  not in provinces and bin == 'c7':
            c7_val = renewable_potential_par_df.loc[index, 'value']
            renewable_potential_par_df.loc[index, 'value'] = 0
            rows_to_add.append({
                'node': [province],
                'commodity': ['wind_onshore'],
                'grade': ['c8'],
                'level': ['renewable'],
                'year': [year],
                'value':[c7_val],
                'unit': ['GWa/a']
            })
        elif tech == 'solar_pv' and province in provinces:
            if bin in solar_bins:
                new_val = renewable_potential_input_solar_dict[province][bin]
                renewable_potential_par_df.loc[index, 'value'] = new_val
            else:
                rows_to_drop.append(index)
        elif tech == 'solar_pv' and province not in provinces and bin == 'c8': #remove extra bim from non-updated provinces
            rows_to_drop.append(index)
        elif tech == 'solar_pv' and province not in provinces and bin == 'c7': #remove extra bim from non-updated provinces
            c8_corresponding_value = renewable_potential_par_df[
            (renewable_potential_par_df['commodity'] == 'solar_pv') &
            (renewable_potential_par_df['grade'] == 'c8') &
            (renewable_potential_par_df['year'] == year) &
            (renewable_potential_par_df['node'] == province)].iloc[0]['value']

            renewable_potential_par_df.loc[index, 'value'] += c8_corresponding_value

    # Drop rows after iteration
    renewable_potential_par_df = renewable_potential_par_df.drop(rows_to_drop).reset_index(drop=True)

    for row in rows_to_add:
        renewable_potential_par_df = pd.concat([renewable_potential_par_df, pd.DataFrame(row)], ignore_index=True)

    model_obj.ctx.source_scenario['scenario'].check_out()
    model_obj.ctx.source_scenario['scenario'].add_par('renewable_potential', renewable_potential_par_df)
    model_obj.ctx.source_scenario['scenario'].commit('Applying Renewable Potential')

    print(
        f"{'#' * 100}\n Added renewable potential to the model!\n{'#' * 100}"
    )
