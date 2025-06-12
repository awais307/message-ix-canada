import numpy as np
import pandas as pd
import message_ix
import ixmp
from message_ix_models.util import broadcast, make_matched_dfs, same_node, same_time

def apply_obps(ctx):
    """
    Apply OBPS policy with cost reductions for below-standard technologies
    and non-negative fixed cost enforcement
    """
    scenario = ctx.source_scenario['scenario']
    data_file_path = ctx.path['OBPS_policy_input_data']
    excel_sheet = ctx['policy_config']['obps_excel_sheet']

    # Read and prepare data
    provinces = scenario.set('node')[2:]
    data_relation = pd.read_excel(data_file_path, sheet_name=excel_sheet)
    data_relation["region"] = data_relation['region'].str.replace(" ", "")

    # Create province grid with Canada fallback
    canada_values = data_relation[data_relation["region"] == "Canada"]
    unique_combos = canada_values[['variable', 'technology', 'time']].drop_duplicates()

    province_grid = pd.DataFrame({'region': provinces, 'key': 1}).merge(
        unique_combos.assign(key=1), on='key'
    ).drop(columns='key')

    data_relation = pd.merge(
        province_grid, data_relation,
        on=['region', 'variable', 'technology', 'time'], how='left'
    ).merge(
        canada_values, on=['variable', 'technology', 'time'],
        suffixes=('', '_CAN'), how='left'
    )

    data_relation['value'] = data_relation['value'].fillna(data_relation['value_CAN'])
    data_relation = data_relation[['region', 'variable', 'technology', 'time', 'value']]

    # Ontario Fixed Process Handling
    ontario_mask = (
        (data_relation['region'] == 'Ontario') & 
        (data_relation['variable'].str.contains('Fixed Process'))
    )
    data_relation = pd.concat([
        data_relation[ontario_mask],
        data_relation[~data_relation['region'].isin(['Ontario'])]
    ], ignore_index=True)

    # Process standards and rates
    standards = data_relation[data_relation["variable"].str.contains("Standard")]
    tightening_rates = data_relation[data_relation["variable"].str.contains("Tightening")]

    # Get emission factors from scenario
    rel_co2cc = scenario.par('relation_activity', 
                           filters={'relation': ['CO2_cc', 'CO2_ind', 'CO2_feedstocks']})
    
    # Merge standards and rates with emission factors
    result = rel_co2cc.merge(
        standards.rename(columns={'value': 'standard'}),
        left_on=['node_rel', 'technology', 'year_act'],
        right_on=['region', 'technology', 'time']
    ).merge(
        tightening_rates.rename(columns={'value': 'rate'}),
        on=['region', 'technology', 'time'],
        suffixes=('_std', '_rate')
    )

    # Calculate projected standard using Excel-specified rate for each year
    result['projected_standard'] = result['standard'] * (1 - result['rate'])

    # Calculate payable emission intensity (can be negative)
    result['payable_emis_intensity'] = result['value'] - result['projected_standard']   

    # Calculate carbon costs (negative values allowed here)
    carbon_costs = ctx['policy_config']['obps_policy_carbon_cost']
    result['carbon_cost'] = result['payable_emis_intensity'] * np.select(
        [result['year_act'] == 2025, 
         result['year_act'] == 2030,
         result['year_act'] >= 2035],
        [carbon_costs[2025], carbon_costs[2030], carbon_costs['more_than_2035']],
        default=0
    )
    # Identify and print below-standard technologies
    below_standard = result[result['payable_emis_intensity'] < 0]
    if not below_standard.empty:
        print("\nTechnologies with emission intensity below standard:")
        print(below_standard[['technology', 'region', 'year_act']]  # Changed to 'region'
            .drop_duplicates()
            .sort_values(['technology', 'region', 'year_act'])
            .to_string(index=False))
    else:
        print("\nAll technologies meet or exceed emission standards")

    # Update fixed costs with validation and non-negative enforcement
    fix_cost_data = pd.read_csv(ctx.path['fix_cost_no_obps_input_data'], header=0)
    valid_techs = scenario.set('technology')
    
    # Filter and merge
    merged_data = fix_cost_data[fix_cost_data['technology'].isin(valid_techs)].merge(
        result[['technology', 'year_act', 'carbon_cost', 'node_loc']],
        on=['technology', 'year_act', 'node_loc'],
        how='left'
    )
    
    # Calculate adjusted costs with protection against negative values
    merged_data['adjusted_value'] = (
        merged_data['value'] 
        + merged_data['carbon_cost'].fillna(0)
    ).clip(lower=0)

    # Commit changes to scenario
    scenario.check_out()
    scenario.add_par('fix_cost', 
        merged_data[['technology', 'year_act', 'year_vtg', 'adjusted_value', 'node_loc', 'unit']]
        .rename(columns={'adjusted_value': 'value'})
    )
    scenario.commit('OBPS policy with cost adjustments')
    print(f"\n{'#' * 100}\nOBPS applied successfully!\n{'#' * 100}\n")



#For tecs below the standrd, make a list to track the tecs. 