import pandas as pd

def apply_obps(ctx):
	"""
	Apply the Output-Based Pricing System (OBPS) policy for the Baseline Canada Scenario
	to the given MESSAGEix scenario.
	This function modifies the scenario's fixed costs based on emissions intensity and carbon pricing.
	
	Args:
		scenario (ixmp.Scenario): The MESSAGEix scenario to apply the OBPS policy to.
		data_file_path (str): Path to the Excel file containing necessary data.

	Returns:
        None
	"""
	scenario = ctx.source_scenario['scenario']
	data_file_path = ctx.path['OBPS_policy_input_data']

	# Read the required data
	provinces = scenario.set('node')[2:]
	excel_sheet = ctx['policy_config']['obps_excel_sheet']
	data_relation = pd.read_excel(data_file_path, sheet_name=excel_sheet)
	data_relation["region"] = data_relation['region'].str.replace(" ", "")
	canada_values = data_relation[data_relation["region"] == "Canada"]
	for r in provinces:
		if r not in data_relation['region'].values:	
			new_row = canada_values.copy()
			new_row["region"] = r
		
			data_relation = pd.concat([data_relation, new_row], ignore_index=True)
	
	# Now you have a dataframe with the correct units which is for Standard, it would be tc/KW or tonne of carbon per Kwyr. 

	rel_co2cc = scenario.par('relation_activity', filters = {'relation':'CO2_cc'})
	tecs_co2cc = rel_co2cc['technology'].unique()
	
	#data_relation = data_relation[data_relation["region"].isin(provinces)]
	tightening_rates = data_relation[data_relation["variable"].str.contains("Tightening")]
	standards = data_relation[data_relation["variable"].str.contains("Standard")]

	# Filter Ontario data to include only "Fixed Process"
	ontario_tightening_rates = tightening_rates[
		(tightening_rates['region'] == 'Ontario') & 
		(tightening_rates['variable'].str.contains('Fixed Process'))
	]

	# For other provinces, include all tightening rates
	other_provinces_tightening_rates = tightening_rates[
		~tightening_rates['region'].isin(['Ontario'])
	]

	# Combine Ontario's fixed process data with other provinces' data
	tightening_rates_co2cc = pd.concat([
		ontario_tightening_rates,
		other_provinces_tightening_rates
	], ignore_index=True)

	tightening_rates_co2cc = tightening_rates_co2cc[tightening_rates_co2cc['technology'].isin(tecs_co2cc)]
	tightening_rates_co2cc.drop(columns = ['variable','unit [tCO2/-]','comments'], inplace = True)
	tightening_rates_co2cc.rename(columns= {'region':'node_rel','value':'rate','time':'year_act'}, inplace=	True)
	
	rel_co2cc = rel_co2cc[rel_co2cc['technology'].isin(tightening_rates_co2cc['technology'].unique())]
	result = rel_co2cc.merge(tightening_rates_co2cc, on = ['node_rel','year_act','technology'])
	
	# Calculate Emission intensity standard
	result['emis_standard'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] > 2020:
			value_cal = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2015), 
				'value'
			]
			if not value_cal.empty:
				result.at[index, 'emis_standard'] = row['value'] - row['rate'] * value_cal.values[0]
			elif row['technology'] == 'oil_extr_7':
				value_cal = result.loc[
					(result['technology'] == row['technology']) & 
					(result['year_act'] == 2030), 
					'value'
				]
				result.at[index, 'emis_standard'] = row['value'] - row['rate'] * value_cal.values[0]
			else:
				value_cal = result.loc[
					(result['technology'] == row['technology']) & 
					(result['year_act'] == 2020), 
					'value'
				]
				result.at[index, 'emis_standard'] = row['value'] - row['rate'] * value_cal.values[0]
	# Calculate Payable emission intensity
	result['payable_emis_intensity'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] > 2020:
			result.loc[index, 'payable_emis_intensity'] = row['value'] - row['emis_standard']

   
	# Calculate carbon cost
	# rate = 0.73
	result['carbon_cost'] = 0.0
	for index, row in result.iterrows():
		if row['year_act'] == 2025:
			result.loc[index, 'carbon_cost'] = row['payable_emis_intensity'] * ctx['policy_config']['obps_policy_carbon_cost'][2025]
		elif row['year_act'] == 2030:
			result.loc[index, 'carbon_cost'] = row['payable_emis_intensity'] *  ctx['policy_config']['obps_policy_carbon_cost'][2030] 
		elif row['year_act'] >= 2035:
			result.loc[index, 'carbon_cost'] = row['payable_emis_intensity'] * ctx['policy_config']['obps_policy_carbon_cost']['more_than_2035']

	'''# Adjust for years 2055 and 2060
	for index, row in result.iterrows():
		if row['year_act'] > 2050:
			value_to_assign = result.loc[
				(result['technology'] == row['technology']) & 
				(result['year_act'] == 2050), 
				'carbon_cost'
			].values
			if len(value_to_assign) > 0:
				result.at[index, 'carbon_cost'] = value_to_assign[0]'''
	
	# Merge with fix_cost data and update the scenario's fix_cost
	fix_cost_no_obps_input_data = ctx.path['fix_cost_no_obps_input_data']
	data_fixcost = pd.read_csv(fix_cost_no_obps_input_data, header=0) #scenario.par('fix_cost')
	data_fixcost = data_fixcost[data_fixcost['technology'].isin(tecs_co2cc)]
	merged_data = pd.merge(
		data_fixcost, 
		result[['technology', 'year_act', 'carbon_cost','node_loc']],
		on=['technology', 'year_act','node_loc'],
		how="left"
	)
	merged_data['adjusted_value'] = merged_data['value'] + merged_data['carbon_cost'].fillna(0)
	merged_data_file_path = ctx.path['obps_standart_merged_data_output']
	merged_data.to_csv(merged_data_file_path)
	fix_cost_df = merged_data[['technology', 'year_act', 'year_vtg', 'adjusted_value','node_loc','unit']]
	fix_cost_df.rename(columns={'adjusted_value':'value'},inplace=True)
	
	scenario.check_out()
	scenario.add_par('fix_cost', fix_cost_df)
	scenario.commit('Add OBPS standard using provincial tighetning rates')
	print(
			f"{'#' * 100}\n Added OBPS policy to the model!\n{'#' * 100}"
		)


