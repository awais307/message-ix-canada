import message_ix
import pandas as pd

from message_ix_models.model.material.material_demand import material_demand_calc

from message_ix_models.model.material.util import get_ssp_from_context, read_config

from message_ix_models.util import (
    broadcast,
    nodes_ex_world,
    package_data_path,
    same_node,
)

from message_ix_models.model.material.data_util import (
    add_ccs_technologies,
    add_cement_bounds_2020,
    add_coal_lowerbound_2020,
    add_elec_i_ini_act,
    add_elec_lowerbound_2020,
    add_emission_accounting,
    add_new_ind_hist_act,
    modify_baseyear_bounds,
    modify_demand_and_hist_activity,
    modify_industry_demand,
)

from message_ix_models.util.compat.message_data import (
    calibrate_UE_gr_to_demand,
    calibrate_UE_share_constraints,
)

from message_ix_models.util.compat.message_data import (
    manual_updates_ENGAGE_SSP2_v417_to_v418 as engage_updates,
)

from message_ix_models.model.build import apply_spec

from message_ix_models.util import package_data_path

from model.policies.material.apply_cement_material import add_data_1, get_spec

##################################################################################

def build(
    scenario: message_ix.Scenario, old_calib: bool, iea_data_path=None
) -> message_ix.Scenario:
    """Set up materials accounting on `scenario`."""

    # Get the specification
    # Apply to the base scenario
    spec = get_spec()

    if "water_supply" not in list(scenario.set("level")):
        scenario.check_out()
        # add missing water tecs
        scenario.add_set("technology", "extract__freshwater_supply")
        scenario.add_set("level", "water_supply")
        scenario.add_set("commodity", "freshwater_supply")

        water_dict = pd.read_excel(
            package_data_path("material", "other", "water_tec_pars.xlsx"),
            sheet_name=None,
        )
        for par in water_dict.keys():
            scenario.add_par(par, water_dict[par])
        scenario.commit("add missing water tecs")

    apply_spec(scenario, spec, add_data_1, fast=True)  # dry_run=True
    if "SSP_dev" not in scenario.model:
        engage_updates._correct_balance_td_efficiencies(scenario)
        #engage_updates._correct_coal_ppl_u_efficiencies(scenario)
        engage_updates._correct_td_co2cc_emissions(scenario)
    # spec = None
    # apply_spec(scenario, spec, add_data_2)
    from message_ix_models import ScenarioInfo

    s_info = ScenarioInfo(scenario)
    nodes = s_info.N

    # Adjust exogenous energy demand to incorporate the endogenized sectors
    # Adjust the historical activity of the useful level industry technologies
    # Coal calibration 2020
    add_ccs_technologies(scenario)
    if old_calib:
        modify_demand_and_hist_activity(scenario)
    else:
        modify_baseyear_bounds(scenario)

        last_hist_year = scenario.par("historical_activity")["year_act"].max()

        #seems to be for chemicals only
        #modify_industry_demand(scenario, last_hist_year, iea_data_path)

        #it refrences a demand file that I don't have
        #add_new_ind_hist_act(scenario, [last_hist_year], iea_data_path)

        #uncomment
        add_elec_i_ini_act(scenario)
        #uncomment
        add_emission_accounting(scenario)

        # scenario.commit("no changes")

    #refrences messing data for China cement bounds    
    #add_coal_lowerbound_2020(scenario)
    #add_cement_bounds_2020(scenario)

    # Market penetration adjustments
    # NOTE: changing demand affects the market penetration
    # levels for the enduse technologies.
    # FIXME: context.ssp only works for SSP1/2/3 currently missing SSP4/5

    # Error with nodes
    # calibrate_UE_gr_to_demand(
    #     scenario,
    #     s_info,
    #     data_path=package_data_path("material"),
    #     ssp="SSP2",
    #     region=identify_nodes(scenario),
    # )

    calibrate_UE_share_constraints(scenario, s_info)

    # scenario.check_out()
    # input_df = scenario.par('input')
    # scenario.remove_par("input")
    # scenario.commit("input processing commit")
    # input_df = input_df[input_df['node_loc'] == input_df['node_origin']]
    # scenario.add_par("input",input_df)

    # scenario.commit("input processing commit")

    # scenario.check_out()

    # output_df = scenario.par('output')
    # scenario.remove_par("output")
    # scenario.commit("output processing commit")
    # output_df = output_df[output_df['node_loc'] == output_df['node_dest']]
    # scenario.add_par("output", output_df)

    # scenario.commit("output processing commit")

    # Electricity calibration to avoid zero prices for CHN.
    # if "R12_CHN" in nodes:
    #     add_elec_lowerbound_2020(scenario)

    # i_feed demand is zero creating a zero division error during MACRO calibration
    scenario.check_out()
    scenario.remove_set("sector", "i_feed")
    scenario.commit("i_feed removed from sectors.")

    df = scenario.par(
        "bound_activity_lo",
        filters={"node_loc": "R12_RCPA", "technology": "sp_el_I", "year_act": 2020},
    )
    scenario.check_out()
    scenario.remove_par("bound_activity_lo", df)
    scenario.commit("remove sp_el_I min bound on RCPA in 2020")
    print("HEYYYY!")
    return scenario
