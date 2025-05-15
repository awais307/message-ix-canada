import pandas as pd
from message_ix import make_df

def add_cer_emission_constraint_and_offsets(
    scen,
    relation_name="cer_direct_emission_intensity",
    tech_list=None,
    offset_techs=None,
    years=None,
    mode="M1",
    emission="TCE",
    output_commodity="electr",
    output_level="secondary",
    output_time="year",
    intensity_limit=0.5694,
):
    """
    Add CER emission constraint relation and offset purchasing options using tax_emission.
    """

    print("🔧 Starting CER constraint and offset implementation...")

    if tech_list is None or years is None or offset_techs is None:
        raise ValueError("❌ tech_list, offset_techs, and years must all be provided.")

    # Filter years
    years = [y for y in years if y >= 2030]
    print(f"📅 Target years filtered to: {years}")

    # Get subnational nodes
    all_nodes = scen.set("node")
    subnational_nodes = [n for n in all_nodes if n not in ["World", "Canada"]]
    print(f"🌎 Operating on subnational nodes: {subnational_nodes}")

    records_relation = []
    records_upper = []
    records_tax = []

    print(f"⚙️ Adding relation_activity entries for techs and offsets...")

    for node in subnational_nodes:
        for year in years:

            # Electricity technologies
            for tec in tech_list:
                records_relation.extend([
                    {
                        "relation": relation_name,
                        "node_rel": node,
                        "node_loc": node,
                        "year_rel": year,
                        "technology": 'CO2_TCE',
                        "year_act": year,
                        "mode": mode,
                        "value": 1.0,
                        "unit": "-"
                    },
                    {
                        "relation": relation_name,
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

            # Offset technologies
            for tec in offset_techs:
                records_relation.append({
                    "relation": relation_name,
                    "node_rel": node,
                    "node_loc": node,
                    "year_rel": year,
                    "technology": tec,
                    "year_act": year,
                    "mode": mode,
                    "value": 1.0,
                    "unit": "-"
                })

                # Assign province-specific offset cost
                if node == "Alberta":
                    tax_cad_2025 = 60
                elif node == "BritishColumbia":
                    tax_cad_2025 = 35
                else:
                    tax_cad_2025 = 85 #USD/tC

                # Convert CAD 2025 to USD 2010
                tax_usd_2010 = (tax_cad_2025 * 0.75) / 1.25

                records_tax.append({
                    "node": node,
                    "type_year": year,
                    "type_tec": 'credits_p',
                    "mode": mode,
                    "type_emission": emission,
                    "value": tax_usd_2010,
                    "unit": "USD/tC"
                })

            records_upper.append({
                "relation": relation_name,
                "node_rel": node,
                "year_rel": year,
                "value": 0,
                "unit": "-"
            })

    print("📋 DataFrames being created...")

    df_relation_activity = pd.DataFrame(records_relation)
    df_relation_upper = pd.DataFrame(records_upper)
    df_tax_emission = pd.DataFrame(records_tax)
    df_cat_tech = make_df('cat_tec',
             type_tec = 'credits_p',
             technology = 'credits_purchase')
    

    
    print(f"🧾 Number of relation_activity entries: {len(df_relation_activity)}")
    print(f"📈 Number of tax_emission entries: {len(df_tax_emission)}")
    print(f"🛑 Setting relation_upper for all nodes and years...")

    print("💾 Committing changes to scenario...")

    with scen.transact("Add CER constraint and offset tax"):
        scen.add_set('technology', offset_techs)
        scen.add_set("relation", relation_name)
        scen.add_set('type_tec', 'credits_p')
        scen.add_set('cat_tec', df_cat_tech)
        scen.add_par("relation_activity", df_relation_activity)
        scen.add_par("relation_upper", df_relation_upper)
        scen.add_par("tax_emission", df_tax_emission)

    print("✅ CER emission constraint and offset implementation complete.")
import pandas as pd

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

# Get electricity generation techs
tech_list_cer = [
    # Fossil and bio without CCS
    'bio_istig', 'coal_adv', 'coal_ppl', 'eth_bio', 'gas_cc',
    'geo_ppl', 'h2_bio', 'h2_coal', 'h2_smr', 'igcc',
    'liq_bio', 'loil_cc', 'loil_ppl', 'meth_coal', 'meth_ng',
    'syn_liq', 'elec_imp', 'gas_ct', 'gas_ppl', 'foil_ppl', 'h2_atr',

    # Partial CCS (optional – remove if full capture assumed)
    'coal_adv_ccs', 'gas_cc_ccs'
]



# Define offset tech(s)
offset_techs = ['credits_purchase']  # or ['offset_ccs', ...]



# Years and nodes
years = scenario.set('year')
nodes = scenario.set('node')

# Apply function
add_cer_emission_constraint_and_offsets(
    scenario,
    tech_list=tech_list_cer,
    offset_techs=offset_techs,
    years=years
)

techs = ["bio_istig_ccs", "eth_bio_ccs", "h2_bio_ccs", "liq_bio_ccs"]
add_technical_lifetime(scenario, techs)