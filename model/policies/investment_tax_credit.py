"""
This module provides functions to implement various energy policies in MESSAGEix scenarios,
including hydrogen shares, federal carbon tax, coal phase-out, and investment tax credits.
"""

import pandas as pd

def disect_years(scenario_years, itc_input_df, ITC, tech):
    scenario_years = scenario_years[scenario_years['technology'] == tech]['year_vtg'].unique()
    itc_policy_years_filtered = itc_input_df[itc_input_df['variable'] == ITC]['time'].unique()
    return [year for year in scenario_years if year in itc_policy_years_filtered]

def par_tech_to_itc_rate(ITC, technologies, inv_cost_par_df, itc_input_df, itc_input_dict):
    return {
        tech: {
            year: itc_input_dict[ITC][year]
            for year in disect_years(inv_cost_par_df, itc_input_df, ITC, tech)
        }
        for tech in technologies['technology'].unique()
    }

def add_investment_tax_credit(model_obj):
    """
    Add an investment tax credit to a MESSAGEix scenario.

    This function modifies the provided MESSAGEix scenario to include an investment tax credit.
    The function is set up to allocate investment tax credits (ITCs) across eligible energy technologies
    in the scenario, grouped by key classes: CCUS, Clean Technology, and various Clean Hydrogen pathways.
    """

    # List of technologies eligible for Clean Technology ITC
    clean_technologies = [
        'wind_cv1', 'wind_cv2', 'wind_cv3', 'wind_cv4',
        'wind_ppf', 'wind_ppl',
        'solar_cv1', 'solar_cv2', 'solar_cv3', 'solar_cv4', 'solar_i',
        'solar_pv_ppl',
        'solar_th_ppl', 'solar_th_ppl__air', 'solar_th_ppl__cl_fresh',
        'solar_th_ppl__ot_fresh', 'solar_th_ppl__ot_saline',
        'hydro_hc', 'hydro_lc'
    ]

    # Load ITC policy input data
    itc_input_df = pd.read_csv(model_obj.ctx.path['ITC_policy_input_data'])
    itc_input_df['value'] = itc_input_df['value'].fillna(0)
    itc_input_dict = {
        variable: {row['time']: row['value']
                   for _, row in itc_input_df[itc_input_df['variable'] == variable].iterrows()}
        for variable in itc_input_df['variable'].unique()
    }

    inv_cost_par_df = model_obj.ctx.source_scenario['scenario'].par('inv_cost')

    # --- CCUS/CCS Technologies ---
    ITC_ccus = "Input|Policy|ITCs|CCUS"
    filter_ccus = inv_cost_par_df['technology'].str.contains('ccs', case=False, na=False)
    ccus_df = inv_cost_par_df[filter_ccus]
    techs_ccus = ccus_df['technology'].unique()
    itc_rate_ccus = par_tech_to_itc_rate(ITC_ccus, ccus_df, inv_cost_par_df, itc_input_df, itc_input_dict)

    # --- Clean Technology (renewables, hydro) ---
    ITC_clean_tech = "Input|Policy|ITCs|Clean Technology"
    clean_tech_df = inv_cost_par_df[inv_cost_par_df['technology'].isin(clean_technologies)]
    techs_clean_tech = clean_tech_df['technology'].unique()
    itc_rate_clean_tech = par_tech_to_itc_rate(ITC_clean_tech, clean_tech_df, inv_cost_par_df, itc_input_df, itc_input_dict)

    # --- Clean Hydrogen: Electrolysis ---
    ITC_h2_elec = "Input|Policy|ITCs|Clean Hydrogen|Elec"
    filter_h2_elec = inv_cost_par_df['technology'].str.contains('h2_elec', case=False, na=False)
    h2_elec_df = inv_cost_par_df[filter_h2_elec]
    techs_h2_elec = h2_elec_df['technology'].unique()
    itc_rate_h2_elec = par_tech_to_itc_rate(ITC_h2_elec, h2_elec_df, inv_cost_par_df, itc_input_df, itc_input_dict)

    # --- Clean Hydrogen: CCS (SMR or ATR with CCS) ---
    ITC_h2_ccs = "Input|Policy|ITCs|Clean Hydrogen|CCS"
    filter_h2_ccs = inv_cost_par_df['technology'].str.contains('h2_smr_ccs|h2_atr_ccs', case=False, na=False)
    h2_ccs_df = inv_cost_par_df[filter_h2_ccs]
    techs_h2_ccs = h2_ccs_df['technology'].unique()
    itc_rate_h2_ccs = par_tech_to_itc_rate(ITC_h2_ccs, h2_ccs_df, inv_cost_par_df, itc_input_df, itc_input_dict)

    # --- Clean Hydrogen: Pyrolysis ---
    ITC_h2_pyro = "Input|Policy|ITCs|Clean Hydrogen|Pyrolysis"
    filter_h2_pyro = inv_cost_par_df['technology'].str.contains('h2_pyrolysis', case=False, na=False)
    h2_pyro_df = inv_cost_par_df[filter_h2_pyro]
    techs_h2_pyro = h2_pyro_df['technology'].unique()
    itc_rate_h2_pyro = par_tech_to_itc_rate(ITC_h2_pyro, h2_pyro_df, inv_cost_par_df, itc_input_df, itc_input_dict)

    # --- Apply ITC policies across all eligible rows ---
    for index, row in inv_cost_par_df.iterrows():
        tech = row['technology']
        year = row['year_vtg']
        # CCUS/CCS ITC
        if tech in techs_ccus and year in itc_rate_ccus.get(tech, {}):
            inv_cost_par_df.iloc[index, 3] *= (100 - itc_rate_ccus[tech][year]) / 100
        # Clean Hydrogen: Electrolysis
        elif tech in techs_h2_elec and year in itc_rate_h2_elec.get(tech, {}):
            inv_cost_par_df.iloc[index, 3] *= (100 - itc_rate_h2_elec[tech][year]) / 100
        # Clean Hydrogen: CCS
        elif tech in techs_h2_ccs and year in itc_rate_h2_ccs.get(tech, {}):
            inv_cost_par_df.iloc[index, 3] *= (100 - itc_rate_h2_ccs[tech][year]) / 100
        # Clean Hydrogen: Pyrolysis
        elif tech in techs_h2_pyro and year in itc_rate_h2_pyro.get(tech, {}):
            inv_cost_par_df.iloc[index, 3] *= (100 - itc_rate_h2_pyro[tech][year]) / 100
        # Clean Technology (renewables, hydro)
        elif tech in techs_clean_tech and year in itc_rate_clean_tech.get(tech, {}):
            inv_cost_par_df.iloc[index, 3] *= (100 - itc_rate_clean_tech[tech][year]) / 100

    # --- Save/commit the parameter update to the scenario ---
    model_obj.ctx.source_scenario['scenario'].check_out()
    model_obj.ctx.source_scenario['scenario'].add_par('inv_cost', inv_cost_par_df)
    model_obj.ctx.source_scenario['scenario'].commit('Applying ITC policies')

    print(
        f"{'#' * 100}\n Added ITC policy to the model!\n{'#' * 100}"
    )

