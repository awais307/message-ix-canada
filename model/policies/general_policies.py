import pandas as pd
from model.utlities.utils import expand_grid

def shares(msgSDG, path, nodeName, suffix):
	"""
	Add share constraints for renewable energy technologies in a MESSAGEix scenario.
	This function modifies the provided MESSAGEix scenario to include share constraints for renewable energy 
	technologies. It sets up the necessary sets and parameters to define the shares for renewable electricity 
	technologies.
	
	Args:
		msgSDG (MESSAGEix.Scenario): The MESSAGEix scenario object to be modified.
		path (str): The path to the directory containing the input Excel file.
		nodeName (str): The name of the node for which the shares are being defined.
		suffix (str): The suffix for the input Excel file name.

	Returns:
		None
	"""
	msgSDG.check_out()
	# Add type_tec for renewable
	type_tec = 'renewable_electr'
	msgSDG.add_set('type_tec', type_tec)
	# Define share for renewable
	shares = 'share_renew_electr'
	msgSDG.add_set('shares', shares)
	# Include technologies for which shares need to be defined
	tec = ('wind_ppf', 'wind_ppl', 'solar_pv_ppl', 'solar_th_ppl', 'hydro_lc', 'hydro_hc')
	msgSDG.add_set('cat_tec', pd.DataFrame({'type_tec': type_tec, 'technology': tec}))
	# Mapping total share from which share is intended
	dic = {
		'shares': [shares],
		'node_share': [nodeName],
		'node': [nodeName],
		'type_tec': ['powerplant'],
		'mode': ['M1'],
		'commodity': ['electr'],
		'level': ['secondary']
	}
	df = expand_grid(dic)
	msgSDG.add_set('map_shares_commodity_total', df)
	# Mapping share from total
	dic = {
		'shares': [shares],
		'node_share': [nodeName],
		'node': [nodeName],
		'type_tec': [type_tec],
		'mode': ['M1'],
		'commodity': ['electr'],
		'level': ['secondary']
	}
	df = expand_grid(dic)
	msgSDG.add_set('map_shares_commodity_share', df)
	# Importing required shares from Excel files
	xls_par = pd.ExcelFile(f"{path}/Parameters{suffix}.xlsx")
	sheet_shares = xls_par.parse('share_comodity_lo')

	msgSDG.add_par('share_commodity_lo', sheet_shares)
	msgSDG.commit('renewable shares defined')
	# TODO: Check the level at which shares need to be defined, usually electricity, a good level is secondary.

def add_policy_for_province():
	"""
	Add policies related to Yukon to a MESSAGEix scenario.
	This function modifies the provided MESSAGEix scenario to include specific energy policies 
	related to the Yukon province. The specific implementation details of these policies, 
	such as the types of policies, the affected sectors, and the time period for implementation, 
	should be added within this function.
	Args:
		scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the Yukon policies will be added.
	Returns:
		None
	"""
	pass


