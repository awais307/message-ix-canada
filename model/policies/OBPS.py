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
        data_relation, province_grid,
        on=['region', 'variable', 'technology', 'time'], how='right'
    ).merge(
        canada_values, on=['variable', 'technology', 'time'],
        suffixes=('', '_CAN'), how='left'
    )

    # 4. Fill missing values with Canada's data
    fill_cols = ['value', 'emission_standard_tec', 'standard_reduction']
    for col in fill_cols:
        data_relation[col] = data_relation[col].fillna(data_relation[f"{col}_CAN"])
    
    data_relation = data_relation[['region', 'variable', 'technology', 'time'] + fill_cols]

        # 6. Use Tightening data directly
    tightening = data_relation[
        data_relation["variable"].str.contains("Tightening")
    ].rename(columns={'time': 'year_act', 'value': 'rate'})

    # 7. Get emission factors
    rel_co2cc = scenario.par('relation_activity', 
                            filters={'relation': ['CO2_cc', 'CO2_ind', 'CO2_feedstocks']})

    # 8. Merge tightening rates with emission factors
    result = rel_co2cc.merge(
        tightening[['region', 'technology', 'year_act', 'rate', 'emission_standard_tec', 'standard_reduction']],
        left_on=['node_rel', 'technology', 'year_act'],
        right_on=['region', 'technology', 'year_act'],
        how='left'
    )

    result = result.merge(
    rel_co2cc[['node_rel', 'technology', 'year_act', 'value']]
        .rename(columns={'value': 'ref_tech_emis', 'technology': 'emission_standard_tec'}),
    left_on=['node_rel', 'emission_standard_tec', 'year_act'],
    right_on=['node_rel', 'emission_standard_tec', 'year_act'],
    how='left'
)

    # 9. Calculate base standard using emission factor and reduction
    result['base_standard'] = result['ref_tech_emis'] * result['standard_reduction']

    # 10. Calculate projected standard
    result['projected_standard'] = result['base_standard'] * (1 - result['rate'])
    result['payable_emis_intensity'] = result['value'] - result['projected_standard']


        # Add this diagnostic print
    print("\nOBPS Calculation Variables for BC gas_cc:")
    for year in [2030, 2035, 2040]:
        subset = result[
            (result['region'] == 'BritishColumbia') &
            (result['technology'] == 'gas_cc') &
            (result['year_act'] == year)
        ]
        if not subset.empty:
            print(
                f"{year}: "
                f"Base={subset['base_standard'].values[0]:.3f}, "
                f"Rate={subset['rate'].values[0]:.3f}, "
                f"Projected={subset['projected_standard'].values[0]:.3f}, "
                f"Actual={subset['value'].values[0]:.3f}, "
                f"Payable={subset['payable_emis_intensity'].values[0]:.3f}"
            )
        else:
            print(f"{year}: No data - check merge filters or input data")


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
    print(f"\n{'#' * 100}\nOBPS applied successfully!\n{'#' * 100}\n")

    #########################
    # Create Carbon Cost DF #
    #########################
    df = pd.read_excel("data/obps_inputs_clean.xlsx", sheet_name="Mapping")
    OBPS_technologies = list(df["technology"].unique())
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
        if technology in OBPS_technologies:# Make sure the group is sorted by year
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