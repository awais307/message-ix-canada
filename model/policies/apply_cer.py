
"""
Module: cer_constraints.py

Provides functions to apply CER emission intensity and offset constraints,
assign technical lifetimes, and a convenience entry point.
"""
import pandas as pd
from message_ix import make_df


def apply_cer(
    scen,
    relation_name_direct: str,
    relation_name_offset: str,
    tech_list: list,
    offset_techs: list,
    years: list,
    mode: str,
    emission: str,
    intensity_limit: float,
    offset_limit: float
):
    """
    Apply CER emission intensity constraints and offset purchase limits to a MESSAGEix Scenario.
    """
    if not (tech_list and offset_techs and years):
        raise ValueError("tech_list, offset_techs, and years must all be provided.")

    # Filter years >= 2030
    years = [y for y in years if int(y) >= 2030]

    # Identify subnational nodes
    all_nodes = scen.set("node")
    subnational = [n for n in all_nodes if n not in {"World", "Canada"}]

    # Prepare records
    rec_dir = []
    rec_off = []
    upp_dir = []
    upp_off = []

    for node in subnational:
        for year in years:
            # Direct emission intensity
            for tec in tech_list:
                rec_dir += [
                    {"relation": relation_name_direct,
                     "node_rel": node, "node_loc": node,
                     "year_rel": year, "technology": emission,
                     "year_act": year, "mode": mode,
                     "value": 1.0, "unit": "-"},
                    {"relation": relation_name_direct,
                     "node_rel": node, "node_loc": node,
                     "year_rel": year, "technology": tec,
                     "year_act": year, "mode": mode,
                     "value": -intensity_limit, "unit": "-"}
                ]
            upp_dir.append({
                "relation": relation_name_direct,
                "node_rel": node,
                "year_rel": year,
                "value": 0,
                "unit": "-"
            })

            # Offset purchase limit
            for tec in offset_techs:
                rec_off.append({
                    "relation": relation_name_offset,
                    "node_rel": node, "node_loc": node,
                    "year_rel": year, "technology": tec,
                    "year_act": year, "mode": mode,
                    "value": 1.0, "unit": "-"
                })
            upp_off.append({
                "relation": relation_name_offset,
                "node_rel": node,
                "year_rel": year,
                "value": offset_limit,
                "unit": "-"
            })

    # DataFrames
    df_dir = pd.DataFrame(rec_dir)
    df_off = pd.DataFrame(rec_off)
    df_upp_dir = pd.DataFrame(upp_dir)
    df_upp_off = pd.DataFrame(upp_off)

    # Category for offsets
    df_cat = make_df("cat_tec", type_tec="credits_b", technology="credits_buy")

    # Transactional update
    with scen.transact("Apply CER constraints and offsets"):
        scen.add_set("technology", offset_techs)
        scen.add_set("relation", relation_name_direct)
        scen.add_set("relation", relation_name_offset)
        scen.add_set("type_tec", "credits_b")
        scen.add_set("cat_tec", df_cat)

        scen.add_par("relation_activity", df_dir)
        scen.add_par("relation_activity", df_off)
        scen.add_par("relation_upper", df_upp_dir)
        scen.add_par("relation_upper", df_upp_off)


def add_technical_lifetime(
    scen,
    techs: list,
    start_year: int = 2025,
    lifetime: int = 25
):
    """
    Assign a technical lifetime to specified technologies across subnational nodes.
    """
    nodes = [n for n in scen.set("node") if n not in {"World", "Canada"}]
    years = [y for y in scen.set("year") if int(y) >= start_year]

    rec = [
        {
            "node_loc": node,
            "technology": tec,
            "year_vtg": y,
            "value": lifetime,
            "unit": "year"
        }
        for node in nodes for tec in techs for y in years
    ]
    df_life = pd.DataFrame(rec)

    with scen.transact("Add technical lifetimes"):
        scen.add_par("technical_lifetime", df_life)


def apply_cer_policy(ctx):
    """
    Convenience wrapper to apply standard CER constraints and lifetimes.
    """
    
    scenario = ctx.source_scenario['scenario']
    # Standard CER technologies
    tech_list_cer = [
        'bio_istig', 'coal_adv', 'coal_ppl', 'gas_cc',
        'liq_bio', 'loil_cc', 'loil_ppl', 'syn_liq',
        'elec_imp', 'gas_ct', 'gas_ppl', 'foil_ppl',
        'coal_adv_ccs', 'gas_cc_ccs'
    ]
    offset_techs = ['credits_buy']
    years = [y for y in scenario.set('year') if int(y) >= 2030]

    apply_cer(
        scen=scenario,
        relation_name_direct="cer_direct_emission_intensity",
        relation_name_offset="cer_offset_limit",
        tech_list=tech_list_cer,
        offset_techs=offset_techs,
        years=years,
        mode="M1",
        emission="CO2_TCE",
        intensity_limit=0.5694,
        offset_limit=0.1
    )

    # Default lifetimes for offset CCS techs
    lifetime_techs = ['bio_istig_ccs', 'eth_bio_ccs', 'h2_bio_ccs', 'liq_bio_ccs']
    add_technical_lifetime(
        scen=scenario,
        techs=lifetime_techs,
        start_year=2025,
        lifetime=25
    )