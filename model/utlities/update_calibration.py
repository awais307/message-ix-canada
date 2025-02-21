# -*- coding: utf-8 -*-

from utilities_main.message_utils import (
    add_vintage,
    calibrate_hist_act_to_others,
    calibrate_hist_act_to_commodity_lvl,
    replace_with_most_common,
    update_share,
)


def model_calibrate(msg, nodeNames, replace_negative=False):
    """
    Calibrating the model after parameterization.

    Parameters
    ----------
    msg : message_ix.Scenario
    nodeNames: list
        List of nodes for updating calibration.
    """
    # Adding historical activity for some technologies, based on activity or input
    # commodity of other technologies
    tech_mapping = {
        "heat_t_d": ["heat_i", "heat_rc"],
        "elec_t_d": ["sp_el_I", "sp_el_RC"],
        "loil_t_d": ["loil_trp", "loil_i", "loil_rc"],
        "biomass_t_d": ["biomass_nc", "biomass_rc", "biomass_i"],
        "land_use_biomass": ["biomass_nc", "biomass_rc", "biomass_i"],
        "coal_t_d": ["coal_rc", "coal_i"],
        "eth_t_d": ["sp_eth_I", "eth_i", "eth_rc"],
    }
    # Calling the relevant utility function
    calibrate_hist_act_to_others(msg, tech_mapping, nodeNames, input_commodity=True)

    # Adding historical activity based on input "commodity" at a certain "level"
    calibrate_hist_act_to_commodity_lvl(
        msg, {"gas_t_d": [["gas"], ["final"]]}, nodeNames
    )

    # ===========================================================================
    # Replacing negative or near zero values in some parameters, which are probably
    # the result of some sort of extrapolation when extending lifetime
    if replace_negative:
        replace_with_most_common(
            msg, tec_list=["loil_ppl", "foil_ppl"], par_list=["capacity_factor"]
        )
        replace_with_most_common(msg, tec_list=["gas_cc"], par_list=["input"])

    # ==========================================================================
    # Adding vintage capacity for some technologies that have historical activity
    tec_list = [
        "elec_t_d",
        "gas_t_d",
        "heat_t_d",
        "loil_t_d",
        # "gas_exp", 'elec_exp',
        "biomass_t_d",
        # "loil_ppl", # There are negative values in capcity factor in some regions
        "hydro_lc",
    ]
    add_vintage(msg, tec_list, nodeNames)

    # ==========================================================================
    # Updating minimum shares of some commodities at the end use sectors
    # including, electric_transport and non-commercial biomass
    relations = {
        "UE_res_comm_th_biomass": ["useful_res_comm_th", "biomass_rc", "_rc"],
        "UE_transport_electric_Minimum": ["useful_transport", "elec_trp", "_trp"],
        "UE_industry_sp_liquid": ["useful_industry_sp", "sp_eth_I", "_I"],
    }
    for relation, items in relations.items():
        tec_list = [x for x in set(msg.set("technology")) if x.endswith(items[2])]
        update_share(msg, relation, items[0], items[1], tec_list, nodes=nodeNames)

    # ==========================================================================
    # Notice: check which of the following is needed?
    # 1. Update of useful demand technologies growth rates
    # See: https://github.com/iiasa/message_data/blob/dev/message_data/tools/utilities/calibrate_UE_gr_to_demand.py

    # 2. Update of useful demand share constraints based on historical data
    # See: https://github.com/iiasa/message_data/blob/dev/message_data/tools/utilities/calibrate_UE_share_constraints.py
