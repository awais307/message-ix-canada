"""
This module provides functions to implement various energy policies in MESSAGEix scenarios,
including hydrogen shares, federal carbon tax, coal phase-out, and investment tax credits.
"""

import pandas as pd


def disect_years(scenario_years, itc_input_df, ITC, tech):
    scenario_years = scenario_years[scenario_years["technology"] == tech][
        "year_vtg"
    ].unique()
    itc_policy_years_filtered = itc_input_df[itc_input_df["variable"] == ITC][
        "time"
    ].unique()
    return [
        year
        for year in scenario_years
        if year in scenario_years and year in itc_policy_years_filtered
    ]


def par_tech_to_itc_rate(
    ITC, technologies, inv_cost_par_df, itc_input_df, itc_input_dict
):
    return {
        tech: {
            year: itc_input_dict[ITC][year]
            for year in disect_years(inv_cost_par_df, itc_input_df, ITC, tech)
        }
        for tech in technologies["technology"].unique()
    }


def add_investment_tax_credit(model_obj):
    """
    Add an investment tax credit to a MESSAGEix scenario.

    This function modifies the provided MESSAGEix scenario to include an investment tax credit.
    The specific implementation details, such as the tax credit rates and the affected technologies or sectors,
    should be added within this function.

    Args:
        scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the investment tax credit will be added.

    Returns:
        None
    """

    clean_tecnologies = [
        "wind_cv1",
        "wind_cv2",
        "wind_cv3",
        "wind_cv4",
        "wind_ppf",
        "wind_ppl",
        "solar_cv1",
        "solar_cv2",
        "solar_cv3",
        "solar_cv4",
        "solar_i",
        "solar_pv_ppl",
        "solar_th_ppl",
        "solar_th_ppl__air",
        "solar_th_ppl__cl_fresh",
        "solar_th_ppl__ot_fresh",
        "solar_th_ppl__ot_saline",
        "hydro_hc",
        "hydro_lc",
        "stor_ppl",
        "hp_el_i",
        "hp_gas_i",
        "geo_hpl",
        "geo_ppl",
    ]

    itc_input_df = pd.read_csv(model_obj.ctx.path["ITC_policy_input_data"])
    itc_input_df["value"] = itc_input_df["value"].fillna(0)
    itc_input_dict = {
        variable: {
            row[1]["time"]: row[1]["value"]
            for row in itc_input_df[itc_input_df["variable"] == variable].iterrows()
        }
        for variable in itc_input_df["variable"].unique()
    }

    inv_cost_par_df = model_obj.ctx.source_scenario["scenario"].par("inv_cost")

    # for CCUS and CCS technologies in the inv_cost parameter
    ITC = "Input|Policy|ITCs|CCUS"
    inv_cost_par_filtered_ccus_df = inv_cost_par_df[
        inv_cost_par_df["technology"].str.contains("ccs")
    ]
    tecnologies_filtered_ccus = inv_cost_par_filtered_ccus_df["technology"].unique()
    par_tech_to_itc_rate_ccus_dict = par_tech_to_itc_rate(
        ITC,
        inv_cost_par_filtered_ccus_df,
        inv_cost_par_df,
        itc_input_df,
        itc_input_dict,
    )

    # for Clean Technology and CCS technologies in the inv_cost parameter
    ITC = "Input|Policy|ITCs|Clean Technology"
    inv_cost_par_filtered_clean_tech_df = inv_cost_par_df[
        inv_cost_par_df["technology"].isin(clean_tecnologies)
    ]
    tecnologies_filtered_clean_tech = inv_cost_par_filtered_clean_tech_df[
        "technology"
    ].unique()
    par_tech_to_itc_rate_clean_tech_dict = par_tech_to_itc_rate(
        ITC,
        inv_cost_par_filtered_clean_tech_df,
        inv_cost_par_df,
        itc_input_df,
        itc_input_dict,
    )

    # for Clean Hydrogen and green hydrogen technologies in the inv_cost parameter
    ITC = "Input|Policy|ITCs|Clean Hydrogen"
    inv_cost_par_filtered_clean_h_df = inv_cost_par_df[
        inv_cost_par_df["technology"].str.contains("h2_elec")
    ]
    tecnologies_filtered_clean_h = inv_cost_par_filtered_clean_h_df[
        "technology"
    ].unique()
    par_tech_to_itc_rate_clean_h_dict = par_tech_to_itc_rate(
        ITC,
        inv_cost_par_filtered_clean_h_df,
        inv_cost_par_df,
        itc_input_df,
        itc_input_dict,
    )

    for index, row in inv_cost_par_df.iterrows():
        tech = row["technology"]
        year = row["year_vtg"]

        if (
            tech in tecnologies_filtered_ccus
            and year in par_tech_to_itc_rate_ccus_dict[tech].keys()
        ):  # CCUS
            inv_cost_par_df.iloc[index, 3] *= (
                100 - par_tech_to_itc_rate_ccus_dict[tech][year]
            ) / 100

        if (
            tech in tecnologies_filtered_clean_h
            and year in par_tech_to_itc_rate_clean_h_dict[tech].keys()
        ):  # Clean Hydrogen
            inv_cost_par_df.iloc[index, 3] *= (
                100 - par_tech_to_itc_rate_clean_h_dict[tech][year]
            ) / 100

        if (
            tech in tecnologies_filtered_clean_tech
            and year in par_tech_to_itc_rate_clean_tech_dict[tech].keys()
        ):  # Clean Technology
            inv_cost_par_df.iloc[index, 3] *= (
                100 - par_tech_to_itc_rate_clean_tech_dict[tech][year]
            ) / 100

    model_obj.ctx.source_scenario["scenario"].check_out()
    model_obj.ctx.source_scenario["scenario"].add_par("inv_cost", inv_cost_par_df)
    model_obj.ctx.source_scenario["scenario"].commit("Applying ITC policies")

    print(f"{'#' * 100}\n Added ITC policy to the model!\n{'#' * 100}")
