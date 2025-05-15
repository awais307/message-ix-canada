import pandas as pd
from message_ix import make_df
import pandas as pd

import pandas as pd
from message_ix import make_df

def add_cer_emission_constraint_and_offsets(
    scen,
    relation_name_direct="cer_direct_emission_intensity",
    relation_name_offset="cer_offset_limit",
    tech_list=None,
    offset_techs=None,
    years=None,
    mode="M1",
    emission="CO2_TCE",
    output_commodity="electr",
    output_level="secondary",
    output_time="year",
    intensity_limit=0.5694,
    offset_limit=0.1
):
    """
    Add CER emission constraint and offset purchasing limits.
    One relation enforces direct emission intensity, another bounds offset usage.
    """

    print("🔧 Starting CER constraint and offset implementation...")

    if tech_list is None or years is None or offset_techs is None:
        raise ValueError("❌ tech_list, offset_techs, and years must all be provided.")

    years = [y for y in years if y >= 2030]
    print(f"📅 Target years filtered to: {years}")

    all_nodes = scen.set("node")
    subnational_nodes = [n for n in all_nodes if n not in ["World", "Canada"]]
    print(f"🌎 Operating on subnational nodes: {subnational_nodes}")

    records_relation_direct = []
    records_relation_offset = []
    records_upper_direct = []
    records_upper_offset = []

    for node in subnational_nodes:
        for year in years:
            # Add relation enforcing intensity limit
            for tec in tech_list:
                records_relation_direct.extend([
                    {
                        "relation": relation_name_direct,
                        "node_rel": node,
                        "node_loc": node,
                        "year_rel": year,
                        "technology": emission,
                        "year_act": year,
                        "mode": mode,
                        "value": 1.0,
                        "unit": "-"
                    },
                    {
                        "relation": relation_name_direct,
                        "node_rel": node,
                        "node_loc": node,
                        "year_rel": year,
                        "technology": tec,
                        "year_act": year,
                        "mode": mode,
                        "value": -1.0 * intensity_limit,
                        "unit": "-"
                    }
                ])

            records_upper_direct.append({
                "relation": relation_name_direct,
                "node_rel": node,
                "year_rel": year,
                "value": 0,
                "unit": "-"
            })

            # Add offset limit relation
            for tec in offset_techs:
                records_relation_offset.append({
                    "relation": relation_name_offset,
                    "node_rel": node,
                    "node_loc": node,
                    "year_rel": year,
                    "technology": tec,
                    "year_act": year,
                    "mode": mode,
                    "value": 1.0,
                    "unit": "-"
                })

            records_upper_offset.append({
                "relation": relation_name_offset,
                "node_rel": node,
                "year_rel": year,
                "value": offset_limit,
                "unit": "-"
            })

    df_relation_direct = pd.DataFrame(records_relation_direct)
    df_relation_offset = pd.DataFrame(records_relation_offset)
    df_upper_direct = pd.DataFrame(records_upper_direct)
    df_upper_offset = pd.DataFrame(records_upper_offset)

    df_cat_tech = make_df("cat_tec", type_tec="credits_b", technology="credits_buy")

    print("💾 Committing changes to scenario...")
    with scen.transact("Add CER emission intensity and offset constraint"):
        scen.add_set("technology", offset_techs)
        scen.add_set("relation", relation_name_direct)
        scen.add_set("relation", relation_name_offset)
        scen.add_set("type_tec", "credits_b")
        scen.add_set("cat_tec", df_cat_tech)

        scen.add_par("relation_activity", df_relation_direct)
        scen.add_par("relation_activity", df_relation_offset)
        scen.add_par("relation_upper", df_upper_direct)
        scen.add_par("relation_upper", df_upper_offset)

    print("✅ CER policy successfully implemented in model.")


def add_technical_lifetime(scen, techs, start_year=2025, lifetime=25):
    """
    Adds a default technical lifetime for offset technologies across all subnational nodes.

    Parameters:
    -----------
    scen : message_ix.Scenario
        The scenario to modify.
    techs : list of str
        List of  technologies to apply lifetimes to.
    start_year : int
        First model year to start assigning lifetimes.
    lifetime : int
        Lifetime duration in years.
    mode : str
        Mode of operation (default = 'M1').
    """
    print("📌 Gathering subnational nodes...")
    nodes = [n for n in scen.set("node") if n not in ["World", "Canada"]]

    print(f"📌 Creating technical_lifetime entries for {len(offset_techs)} technologies across {len(nodes)} nodes...")
    model_years = [y for y in scen.set("year") if int(y) >= start_year]

    records = []
    for node in nodes:
        for tec in techs:
            for year in model_years:
                records.append({
                    "node_loc": node,
                    "technology": tec,
                    "year_vtg": year,
                    "value": lifetime,
                    "unit": "year"
                })

    df_lifetime = pd.DataFrame(records)
    print(f"✅ Adding {len(df_lifetime)} entries to 'technical_lifetime'...")
    
    with scen.transact("Add technical_lifetime for offset technologies"):
        scen.add_par("technical_lifetime", df_lifetime)
    

def main ():

    # === Import and setup ===
    import pandas as pd# Make sure function is modularized

    # === Define electricity generation technologies for CER constraint ===
    tech_list_cer = [
        # Fossil and bio-based generators without full CCS
        'bio_istig', 'coal_adv', 'coal_ppl', 'gas_cc',
        'liq_bio', 'loil_cc', 'loil_ppl', 'syn_liq',
        'elec_imp', 'gas_ct', 'gas_ppl', 'foil_ppl',

        # Partial CCS technologies (only if they do not fully eliminate emissions)
        'coal_adv_ccs', 'gas_cc_ccs'
    ]

    # === Define offset technology (e.g., credit market) ===
    offset_techs = ['credits_buy']

    # === Extract model sets ===
    years = scenario.set('year')
    nodes = scenario.set('node')

    # === Optional: Filter for relevant years and provinces ===
    # This keeps only future years (e.g., from 2030 onwards)
    target_years = sorted([y for y in years if int(y) > 2030])
    subnational_nodes = sorted([n for n in nodes if n not in {"World", "Canada"}])

    # === Call the CER implementation function ===
    add_cer_emission_constraint_and_offsets(
        scenario,
        relation_name_direct="cer_direct_emission_intensity",
        relation_name_offset="cer_offset_limit",
        tech_list=tech_list_cer,
        offset_techs=offset_techs,
        years=target_years,
        mode="M1",
        emission="CO2_TCE",
        output_commodity="electr",
        output_level="secondary",
        output_time="year",
        intensity_limit=0.5694,
        offset_limit=0.1  # Adjust to match CER threshold (e.g., 0.042 MtCO₂/GWh = ~0.5694 MtC/GWyr)
    )

    print("✅ CER policy constraints added to scenario.")


    techs = ["bio_istig_ccs", "eth_bio_ccs", "h2_bio_ccs", "liq_bio_ccs"]
    add_technical_lifetime(scenario, techs)