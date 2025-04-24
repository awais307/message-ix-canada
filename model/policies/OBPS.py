import numpy as np
import pandas as pd
import message_ix
import ixmp
from message_ix_models.util import broadcast, make_matched_dfs, same_node, same_time

def apply_obps(ctx):
    """
    Apply OBPS policy with missing emission factor handling
    """
    scenario = ctx.source_scenario['scenario']
    data_file_path = ctx.path['OBPS_policy_input_data']
    excel_sheet = ctx['policy_config']['obps_excel_sheet']

    # 1. Load and prepare policy data
    data_relation = pd.read_excel(data_file_path, sheet_name=excel_sheet)
    data_relation["region"] = data_relation['region'].str.replace(" ", "")

    # 2. Filter to model's temporal scope
    data_relation['time'] = data_relation['time'].astype(int)
    model_years = scenario.set('year').astype(int)
    data_relation = data_relation[data_relation['time'].isin(model_years)]

    # 3. Create province grid with Canada fallback
    provinces = scenario.set('node')[2:]
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

    # 4. Fill missing values with Canada's data
    fill_cols = ['value', 'emission_standard_tec', 'standard_reduction']
    for col in fill_cols:
        data_relation[col] = data_relation[col].fillna(data_relation[f"{col}_CAN"])
    
    data_relation = data_relation[['region', 'variable', 'technology', 'time'] + fill_cols]

    # 5. Ontario Fixed Process Handling
    ontario_mask = (
        (data_relation['region'] == 'Ontario') & 
        (data_relation['variable'].str.contains('Fixed Process'))
    )
    data_relation = pd.concat([
        data_relation[ontario_mask],
        data_relation[~data_relation['region'].isin(['Ontario'])]
    ], ignore_index=True)

    # 6. Process standards with error handling
    standards = data_relation[
        data_relation["variable"].str.contains("Standard") & 
        (data_relation["value"] != 0)
    ].copy()
    
    # 7. Get emission factors
    rel_co2cc = scenario.par('relation_activity', 
                           filters={'relation': ['CO2_cc', 'CO2_ind', 'CO2_feedstocks']})
    
    # 8. Process standards with missing emission factor handling
    standards_list = []
    skipped_standards = []

    for idx, row in standards.iterrows():
        try:
            # Attempt to get reference tech emission factor
            ref_filter = (
                (rel_co2cc['node_rel'] == row['region']) &
                (rel_co2cc['technology'] == row['emission_standard_tec']) &
                (rel_co2cc['year_act'] == row['time'])
            )
            ref_emis = rel_co2cc.loc[ref_filter, 'value'].values[0]
            
            standards_list.append({
                'region': row['region'],
                'technology': row['technology'],
                'base_year': row['time'],
                'base_standard': ref_emis * row['standard_reduction'],
                'ref_tech': row['emission_standard_tec']
            })
            
        except IndexError:
            # Record skipped standard
            skipped_standards.append({
                'region': row['region'],
                'policy_tech': row['technology'],
                'ref_tech': row['emission_standard_tec'],
                'year': row['time']
            })
            continue

    # 9. Report skipped standards
    if skipped_standards:
        print("\nWARNING: Skipped standards due to missing emission factors:")
        print(pd.DataFrame(skipped_standards))
    else:
        print("\nAll standards processed successfully")

    if not standards_list:
        raise ValueError("No valid standards remaining after filtering")

    standards_df = pd.DataFrame(standards_list)

    # 10. Process tightening rates
    tightening_rates = data_relation[
        data_relation["variable"].str.contains("Tightening")
    ].rename(columns={'time': 'year_act', 'value': 'rate'})

    # 11. Merge data and calculate standards
    result = rel_co2cc.merge(
        standards_df,
        left_on=['node_rel', 'technology', 'year_act'],
        right_on=['region', 'technology', 'base_year'],
        how='inner',
        suffixes=('_emis', '_std')
    ).merge(
        tightening_rates[['region', 'technology', 'year_act', 'rate']],
        on=['region', 'technology', 'year_act'],
        how='left'
    ).fillna({'rate': 0})

    # 12. Calculate projected standards
    result['projected_standard'] = result['base_standard'] * (1 - result['rate'])
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
    var_cost_data = pd.read_csv(ctx.path['var_cost_no_obps_input_data'], header=0)
    valid_techs = scenario.set('technology')
    
    # Filter and merge
    merged_data = var_cost_data[var_cost_data['technology'].isin(valid_techs)].merge(
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
    scenario.add_par('var_cost', 
        merged_data[['technology', 'year_act', 'year_vtg', 'adjusted_value', 'mode', 'time', 'node_loc', 'unit']]
        .rename(columns={'adjusted_value': 'value'})
    )
    scenario.commit('OBPS policy with cost adjustments')

    #########################
    # Create Carbon Cost DF #
    #########################
    df = pd.read_excel("data/obps_inputs_clean.xlsx", sheet_name="Mapping")
    tec_to_IDEA = {row['technology']: row['variable'] for _, row in df.iterrows()}
    ctx.tec_to_IDEA = tec_to_IDEA
    #ctx.carbon_cost = result[['technology', 'year_act', 'carbon_cost','node_loc']]
    carbon_cost = result[['technology', 'year_act', 'carbon_cost','node_loc']]

    # IDEA_df = pd.DataFrame()

    # grouped_df = carbon_cost.groupby(['node_loc', 'technology'], as_index=False)
    years = list(carbon_cost['year_act'].unique())
    # for group in list(grouped_df):
    # 	row = [dict(list(group)[i])['carbon_cost'] for i in range(len(years))]
    # 	row.extend(["Model", group[0][0], "Scenario", "Unit", "Variable",])#'Model', 'Region', 'Scenario', 'Unit', 'Variable'
    # 	IDEA_df.append(row)

    # Group the DataFrame by node_loc and technology
    grouped = carbon_cost.groupby(['node_loc', 'technology'])

    # Create the new empty DataFrame with column headers
    IDEA_columns = years + ['Model', 'node_loc', 'Scenario', 'Unit', 'Variable']
    IDEA_df = pd.DataFrame(columns=IDEA_columns)

    # Loop over each group and build a row
    for (node_loc, technology), group in grouped:
        # Make sure the group is sorted by year
        group_sorted = group.sort_values('year_act')

        # Extract carbon_cost per year (aligning with the years list)
        year_costs = []
        for year in years:
            value = group_sorted.loc[group_sorted['year_act'] == year, 'carbon_cost']
            year_costs.append(value.values[0] if not value.empty else None)

        # Extend with metadata
        row = year_costs + ["Model", node_loc, "baseline_1", "Unit", technology]

        # Append the row
        IDEA_df.loc[len(IDEA_df)] = row
    IDEA_df.to_csv("./data/OBPS_credits.csv")

    print(f"\n{'#' * 100}\nOBPS applied successfully!\n{'#' * 100}\n")

