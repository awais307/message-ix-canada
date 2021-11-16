import pandas as pd
import pyam
from pathlib import Path
from message_ix import make_df

def format_hist_act(DATA):
    
    # Read in Statistics Canada data and sort it
    data = pd.read_csv(DATA / 'statcan_data.csv')
    data['technology'] = data['Fuel type'] + '|' + data['Supply and demand characteristics']
    data = data[['year', 'node', 'technology', 'unit', 'VALUE']]

    # Variable names to change
    changes = {'Total coal|Exports': 'coal_exp',
               'Total coal|Imports': 'coal_imp', 
               'Total coal|Transformed to electricity by utilities': 'coal_ppl',
               'Total coal|Non-energy use': 'coal_fs',
               'Total coal|Total industrial': 'coal_i',
               'Total coal|Production': 'coal_extr_mpen',
               'Primary electricity, hydro and nuclear|Exports': 'elec_exp',
               'Primary electricity, hydro and nuclear|Imports': 'elec_imp',
               'Primary electricity, hydro and nuclear|Total transportation': 'elec_trp',
               'Natural gas|Exports': 'gas_exp',
               'Natural gas|Imports': 'gas_imp',
               'Natural gas|Non-energy use': 'gas_fs',
               'Natural gas|Total transportation': 'gas_trp',
               'Natural gas|Production': 'gas_extr_mpen',
               'Crude oil|Exports': 'oil_exp',
               'Crude oil|Imports': 'oil_imp',
               'Crude oil|Production': 'oil_extr_mpen',
               'Heavy fuel oil|Exports': 'foil_exp',
               'Heavy fuel oil|Imports': 'foil_imp',
               'Heavy fuel oil|Non-energy use': 'foil_fs',
               'Heavy fuel oil|Transformed to electricity by industry': 'foil_ppl_i',
               'Heavy fuel oil|Transformed to electricity by utilities': 'foil_ppl_rc',
               'Heavy fuel oil|Total transportation': 'foil_trp'
              }

    entries = []

    # add rows to list to be used for statcan dataframe
    for x in range(0, len(data)):
        if data.at[x,'technology'] in list(changes.keys()):
            data.at[x,'technology'] = changes[data.at[x,'technology']]
            entry = data.iloc[[x]].copy()
            entries.append(entry)

    # create statcan dataframe
    stat_can = pd.concat(entries, ignore_index = True)

    # check if changes worked correctly
    len(stat_can['technology'].unique()) == len(changes)
    
    # Read canadian historical data from previous run to new dataframe
    msg_test_v4 = pd.read_excel(DATA / 'MESSAGE_CA__test__v4.xlsx', sheet_name = 'historical_activity')
    msg_test_v4.drop(['mode', 'time'], axis = 'columns')
    msg_test_v4.rename(columns = {'year_act': 'year', 'node_loc': 'node', 'value': 'VALUE'}, inplace = True)
    msg_test_v4 = msg_test_v4[['year', 'node', 'technology', 'unit', 'VALUE']]
    
    # Create IAM dataframes
    iam = pyam.IamDataFrame(stat_can, scenario = 'none', region = 'node', value = 'VALUE', model = 'MESSAGEix', variable = 'technology')
    iam_can = pyam.IamDataFrame(msg_test_v4, scenario = 'none', region = 'node', value = 'VALUE', model = 'MESSAGEix', variable = 'technology')

    # convert terajoules in StatCan dataframe
    iam.rename(unit = {'Terajoules': 'TJ'}, inplace = True)
    iam = iam.convert_unit('TJ', to = 'GWh').convert_unit('GWh', to = 'GWa', factor = 1/8760)

    # aggregate foil_ppl
    iam.add('foil_ppl_i', 'foil_ppl_rc', 'foil_ppl', append = True)

    # rename powerplants in regions with only industrial or utility foil_ppl
    foil_ppl = iam.filter(region = ['Alberta', 'British Columbia', 'Manitoba', 'Newfoundland and Labrador'], 
                          variable = ['foil_ppl_i', 'foil_ppl_rc']
                         ).rename(variable = {'foil_ppl_i': 'foil_ppl', 'foil_ppl_rc': 'foil_ppl'})
    iam.append(foil_ppl, inplace = True)

    # Only include variables from message not in statistics canada data
    iam.append(iam_can.filter(variable = [x for x in iam_can.variable if x not in iam.variable]), inplace = True)
    iam = iam.filter(variable = [x for x in iam_can.variable])
    
    provinces = iam.region
    # Previously calculated demand data to be used as proxys
    ratios = pyam.IamDataFrame(DATA / 'proxys.xlsx')

    # match format of previous dataframes
    ratios.rename(region = {'NWT': 'Northwest Territories',
                   'PEI': 'Prince Edward Island',
                   'BC': 'British Columbia'}, inplace = True)
    ratios = ratios.filter(variable = ['i_feed', 'i_spec', 'i_therm', 'rc_spec', 'rc_therm', 'transport'], region = provinces)
    
    iam.append(ratios, inplace = True)
    
    # This dataframe will contain downscaled data to fill in missing values from statcan data
    missing = pyam.IamDataFrame(msg_test_v4, model = 'MESSAGEix', scenario = 'none', region = 'node', variable = 'technology')
    missing_vars = list(changes.values())
    missing_vars.append('foil_ppl')
    missing = missing.filter(variable = missing_vars)
    missing.append(ratios, inplace = True, ignore_meta_conflict = True)
    
    ## Downscaling to fill in missing data (only for 2015, could create problems)
    # i_spec
    technologies = ['coal_exp', 
                    'coal_extr_mpen', 
                    'coal_imp', 
                    'coal_ppl', 
                    'elec_exp', 
                    'elec_imp', 
                    'foil_exp', 
                    'foil_imp', 
                    'foil_ppl',
                    'gas_exp',
                    'gas_extr_mpen',
                    'gas_imp',
                    'oil_exp',
                    'oil_imp',
                    'oil_extr_mpen']
    for tech in technologies:
        missing.downscale_region(variable = tech, region = 'Canada', proxy = 'i_spec', append = True)

    # rc_therm
    technologies = ['heat_rc', 'loil_rc']
    for tech in technologies:
        missing.downscale_region(variable = tech, region = 'Canada', proxy = 'rc_therm', append = True)

    # i_therm
    technologies = ['coal_i']
    for tech in technologies:
        missing.downscale_region(variable = tech, region = 'Canada', proxy = 'i_therm', append = True)

    #i_feed
    technologies = ['coal_fs', 'foil_fs', 'gas_fs']
    for tech in technologies:
        missing.downscale_region(variable = tech, region = 'Canada', proxy = 'i_feed', append = True)

    # transport
    technologies = ['elec_trp', 'foil_trp', 'gas_trp']
    for tech in technologies:
        missing.downscale_region(variable = tech, region = 'Canada', proxy = 'transport', append = True)
        
    missing = missing.filter(variable = missing_vars, region = provinces, year = 2015)
    
    ## Downscale from Canada MESSAGE results
    # rc_spec
    technologies = ['bio_ppl', 'hydro_lc', 'nuc_lc', 'wind_ppl', 'solar_pv_ppl','land_use_biomass']
    for tech in technologies:
        iam.downscale_region(variable = tech, region = 'Canada', proxy = 'rc_spec', append = True)

    # i_spec
    technologies = ['gas_cc', 'gas_ct', 'loil_ppl', 'ref_hil', 'ref_lol']
    for tech in technologies:
        iam.downscale_region(variable = tech, region = 'Canada', proxy = 'i_spec', append = True)

    # rc_therm
    technologies = ['heat_rc', 'loil_rc']
    for tech in technologies:
        iam.downscale_region(variable = tech, region = 'Canada', proxy = 'rc_therm', append = True)

    # i_therm
    technologies = ['biomass_i',
                    'biomass_nc',
                    'biomass_rc',
                    'biomass_t_d',
                    'coal_t_d',
                    'elec_i',
                    'elec_t_d',
                    'eth_bio',
                    'eth_exp',
                    'eth_i',
                    'eth_imp',
                    'ethanol_fs',
                    'foil_i',
                    'foil_rc',
                    'foil_t_d',
                    'gas_i',
                    'gas_rc',
                    'gas_t_d',
                    'heat_i',
                    'heat_t_d',
                    'hp_el_i',
                    'hp_gas_i',
                    'loil_exp',
                    'loil_i',
                    'loil_imp',
                    'loil_t_d'
                   ]
    for tech in technologies:
        iam.downscale_region(variable = tech, region = 'Canada', proxy = 'i_therm', append = True)

    #i_feed
    technologies = ['loil_fs']
    for tech in technologies:
        iam.downscale_region(variable = tech, region = 'Canada', proxy = 'i_feed', append = True)

    # transport
    technologies = ['eth_ic_trp', 'loil_trp']
    for tech in technologies:
        iam.downscale_region(variable = tech, region = 'Canada', proxy = 'transport', append = True)

    data_2015 = iam.filter(variable = [x for x in iam_can.variable], year = 2015)

    # Fill in missing values in 2015 dataframe
    for reg in provinces:
        for var in list(missing.filter(region = reg).variable):
            if var not in list(data_2015.filter(region = reg).variable):
                data_2015.append(missing.filter(region = reg, variable = var), inplace = True)

    # Match MESSAGE spatial sets naming
    data_2015.rename(region = {'British Columbia': 'BritishColumbia',
                           'New Brunswick': 'NewBrunswick',
                           'Newfoundland and Labrador': 'NewfoundlandandLabrador',
                           'Northwest Territories': 'NorthwestTerritories',
                           'Nova Scotia': 'NovaScotia',
                           'Prince Edward Island': 'PrinceEdwardIsland'}, inplace = True)

    historical_activity = data_2015.as_pandas()

    historical_activity = historical_activity[['region', 'variable', 'year', 'value', 'unit']]

    # Make historical activity dataframe
    hist_act = make_df('historical_activity',
                       node_loc = historical_activity['region'],
                       technology = historical_activity['variable'],
                       year_act = historical_activity['year'], 
                       mode = 'M1',
                       time = 'year', 
                       value = historical_activity['value'], 
                       unit = 'GWa'
                      )
    
    return hist_act