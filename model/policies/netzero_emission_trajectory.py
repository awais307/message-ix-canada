"""
This module provides a function to bound emissions in an extreme climate mitigation scenario.
"""

import pandas as pd


def assign_cumulative_netzero(ctx):
    """
    Bound emissions in a climate mitigation scenario.

    This function creates and commits a parameter 'bound_emission' for a given node in the MESSAGEix model.

    Args:
        msgSDG (message_ix.Scenario): The MESSAGEix scenario object.
        nodeName (str): The name of the node to bound emissions for.

    """
    scenario = ctx.source_scenario["scenario"]
    # Define emissions data for Net-Zero scenario
    start_year = 2025
    target_year = 2050
    end_year = 2060

    initial_emission = 720  # MtCO2e in 2025
    net_zero_emission = 0  # Target emissions in 2050

    # Assuming a linear decline from 2025 to 2050
    years = list(range(start_year, end_year + 1))
    emissions_netzero = []

    # Calculate the annual decline rate for Net-Zero
    decline_rate_netzero = (net_zero_emission - initial_emission) / (
        target_year - start_year
    )

    # Calculate emissions for each year
    for year in years:
        if year <= target_year:
            emissions_netzero.append(
                initial_emission + (year - start_year) * decline_rate_netzero
            )
        else:  # Assuming zero emissions after 2050
            emissions_netzero.append(net_zero_emission)

    # Calculate cumulative emissions for Net-Zero scenario
    cumulative_budget_netzero = sum(emissions_netzero)

    # Convert MtCO2e to MtC
    cumulative_budget_netzero_mtC = cumulative_budget_netzero * 0.2727

    # Display results
    print(
        f"{cumulative_budget_netzero_mtC} million tonne of Carbon for Net Zero by 2050"
    )

    # Recreate the original DataFrame with the given trajectory
    data = {
        "type_year": list(range(2025, 2061, 5)),
        "value": [659, 511, 363, 250, 200, 110, 110, 50],  # Original values in MtCO2
    }

    # Create DataFrame
    df_bound_net = pd.DataFrame(data)

    # Add required columns
    df_bound_net.insert(0, "node", "Canada")
    df_bound_net.insert(1, "type_emission", "TCE")
    df_bound_net.insert(2, "type_tec", "all")

    # Convert values from MtCO2 to MtC
    df_bound_net["value"] = df_bound_net["value"] * (12 / 44)

    with scenario.transact():

        # netzero_1.remove_par('tax_emission', df)
        # netzero_1.add_par('bound_emission', df)
        scenario.add_par("bound_emission", df_bound_net)


def apply_industrial_emission_constraint(ctx):
    """
    Add industrial emission constraints based on a predefined Canada trajectory from previous net zero
    """
    scenario = ctx.source_scenario["scenario"]

    df_emis = pd.read_csv(ctx.path["industrial_emission_constraint"])

    with scenario.transact("Add industrial emission bounds"):
        scenario.add_par("bound_emission", df_emis)
