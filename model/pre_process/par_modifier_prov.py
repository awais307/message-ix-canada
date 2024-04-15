## This script needs to be cleaned up and converted into functions which a scenario can be then parameterized with 

df = pd.read_excel(DATA /'provincial_sources/historical_import_export.xlsx')

# Select columns up to 'unit'
df = df[['node_loc', 'technology', 'year_vtg', 'value', 'unit']].rename(columns={'year_vtg': 'year_act'})

# Add 'mode' column with all values set to 'M1'
df['mode'] = 'M1'
df['unit'] ='GWa'
# Add 'time' column with values from 'year_vtg'
df['time'] = 'year'
df['node_loc'] = df['node_loc'].str.replace(' ', '')['node_loc'] = df['node_loc'].str.replace(' ', '')
df['value'] = df['value'].fillna(0)


msg.add_par('historical_activity', df)



import pandas as pd

# Sample data to replicate across Canadian provinces
data = [
    ('R11_NAM', 'elec_t_d', 1990, 'M1', 'year', 346.902),
    ('R11_NAM', 'elec_t_d', 1995, 'M1', 'year', 414.603),
    ('R11_NAM', 'elec_t_d', 2000, 'M1', 'year', 455.097),
    ('R11_NAM', 'elec_t_d', 2005, 'M1', 'year', 482.681),
    ('R11_NAM', 'elec_t_d', 2010, 'M1', 'year', 484.257),
    ('R11_NAM', 'elec_t_d', 2015, 'M1', 'year', 485.843),
    ('R11_NAM', 'elec_t_d', 2020, 'M1', 'year', 521.053)
]

# Canadian provinces and territories with no spaces in names
provinces = [
    'Alberta', 'BritishColumbia', 'Manitoba', 'NewBrunswick', 
    'NewfoundlandandLabrador', 'NovaScotia', 'Ontario', 
    'PrinceEdwardIsland', 'Quebec', 'Saskatchewan', 
    'NorthwestTerritories', 'Nunavut', 'Yukon'
]

# Create a DataFrame for the sample data
df = pd.DataFrame(data, columns=['node_loc', 'technology', 'year_act', 'mode', 'time', 'value'])

# List to store DataFrames for each province
province_dfs = []

# Replicate the data for each Canadian province
for province in provinces:
    temp_df = df.copy()
    temp_df['node_loc'] = province
    province_dfs.append(temp_df)

# Concatenate all provincial DataFrames into one
final_df = pd.concat(province_dfs, ignore_index=True)

msg.add_par('historical_activity', final_df)


# Removing import, export bounds 

# msg.check_out()
df = msg.par('initial_activity_lo')
msg.remove_par('initial_activity_lo', df)
filtered_df = df[~df['technology'].isin(['elec_imp','elec_exp'])]
msg.add_par('initial_activity_lo',filtered_df) 
# msg.check_out()
df = msg.par('initial_activity_up')
msg.remove_par('initial_activity_up', df)
filtered_df = df[~df['technology'].isin(['elec_imp','elec_exp'])]
msg.add_par('initial_activity_up',filtered_df) 

# msg.check_out()
df = msg.par('growth_activity_lo')
msg.remove_par('growth_activity_lo', df)
filtered_df = df[~df['technology'].isin(['elec_imp','elec_exp'])]
msg.add_par('growth_activity_lo',filtered_df) 

# msg.check_out()
df = msg.par('growth_activity_up')
msg.remove_par('growth_activity_up', df)
filtered_df = df[~df['technology'].isin(['elec_imp','elec_exp'])]
msg.add_par('growth_activity_up',filtered_df)

nodes = msg.set('node').tolist()

# Assuming you want to pass all nodes except 'World' and 'R11_GLB'
all_nodes = msg.set('node')
nodes_to_pass = [node for node in all_nodes if node not in ['World', 'R11_GLB']]

model_calibrate(msg, nodes)

# Relations to be removed from copying
relation_remove = ["_min", "_max", "lim_", "_pot", "min-"]
# cleanup_rel_tec(msg, nodes= nodes_to_pass, relation_remove=relation_remove)
remove_accounting = False
# Ensure DataFrame operations use 'reg' correctly
exclusion = []
relations = msg.set('relation').tolist()

if remove_accounting:
    rel_par = pd.DataFrame()
    for par in ['relation_upper', 'relation_lower', 'relation_cost']:
        # Ensure that DataFrame filtering here is correct
        df = msg.par(par)
        df = df[df['node_rel'].isin(reg)][['node_rel', 'relation']]
        rel_par = pd.concat([rel_par, df], ignore_index=True)

    rel_par = rel_par.drop_duplicates()

    rel_act = pd.DataFrame()
    for par in ['relation_new_capacity', 'relation_total_capacity', 'relation_activity']:
        df = msg.par(par)
        df = df[df['node_rel'].isin(reg)][['node_rel', 'relation']]
        rel_act = pd.concat([rel_act, df], ignore_index=True)

    rel_act = rel_act.drop_duplicates()

    exclusion = pd.concat([rel_act, rel_par]).drop_duplicates(keep=False)['relation'].tolist()
    exclusion += [r for r in relations if r not in rel_act['relation'].tolist() and r not in rel_par['relation'].tolist()]

# Add manual exclusions and process them
exclusion += ['PE_domestic_total', 'PE_import_total', 'PE_import_share', 'PE_export_total',
                'demb_limit', 'demF_limit', 'demI_limit', 'demp_limit', 'demR_limit', 'demt_limit',
                'elec_coal', 'elec_gas', 'elec_hydro', 'elec_nuclear', 'ele_nuc', 'foil_prod',
                'oil_based_elec_gen', 'gas_export', 'SO2_red_ref', 'SO2_red_synf', 'SO2_ind',
                'SO2_elec', 'SO2_import', 'SO2_r_c'] + [x for x in relation_remove if x in msg.set("relation")]

msg.check_out()
for rel in set(exclusion):
    if rel in msg.set('relation'):
        msg.remove_set('relation', rel)
        print('Relation: {} - deleted'.format(rel))

msg.commit('Remove unused elements')





