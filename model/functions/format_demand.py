import pandas as pd
import pyam
from message_ix import make_df
from pathlib import Path

# A function used to format demand data for MESSAGE
def format_demand(DATA, scale):
    """This function creates demand dataframes that MESSAGE can use as parameters
        DATA : Path to MESSAGEix data folder
        scale == 'CAN' -> Return Canadian dataframe
        scale == 'PROV' -> Return Provincial dataframe
    """
    
    # Basic model data
    MODEL = 'MESSAGEix'
    SCEN = 'None'
    MSG_YEARS = list(range(2020, 2061, 5))
    
    # Read in data for specific and transport demand
    spec = pyam.IamDataFrame(DATA / 'can_energy_future.xlsx', 
                             model = MODEL, 
                             scenario = SCEN, 
                             region = 'node')
    
    # List of variable name changes
    spec.rename(variable = {'Transportation|Total End-Use': 'transport',
                            'Residential|Electricity': 'sp_el_r',
                            'Commercial|Electricity': 'sp_el_c',
                            'Residential|Biofuels & Emerging Energy': 'solar_pv_r',
                            'Commercial|Biofuels & Emerging Energy': 'solar_pv_c',
                            'Industrial|Electricity': 'sp_el_I',
                            'Industrial|Biofuels & Emerging Energy': 'solar_pv_I'},
                            inplace = True)
            
    # Aggregate variables to get specific res/comm and tranport demands
    spec.add('solar_pv_r', 'solar_pv_c', 'solar_pv_rc', ignore_units = 'PJ', append = True)
    spec.add('sp_el_r', 'sp_el_c', 'sp_el_rc', ignore_units = 'PJ', append = True)
    spec.add('sp_el_rc', 'solar_pv_rc', 'rc_spec', ignore_units = 'PJ', append = True)
    spec.add('sp_el_I', 'solar_pv_I', 'i_spec', ignore_units = 'PJ', append = True)
    
    # Filter to only aggregated variables
    spec = spec.filter(variable = ['rc_spec', 'i_spec', 'transport'])
    
    # Convert units
    spec = spec.convert_unit('PJ', to = 'GWh').convert_unit('GWh', to = 'GWa', factor = 1/8760)
    
    # Read in Canadian demand data from previous model run (for downscaling)
    can_data = pd.read_excel(DATA / 'MESSAGE_CA__test__v4.xlsx',
                             sheet_name = 'demand',
                             usecols=['node', 'commodity', 'year', 'unit', 'value'])
    
    # Convert to IAM format
    can_data = pyam.IamDataFrame(can_data,
                                 model = MODEL,
                                 scenario = SCEN,
                                 region = 'node',
                                 variable = 'commodity'
                                 ).filter(variable = ['i_feed', 'rc_therm', 'i_therm'], year = MSG_YEARS)
    
    # Thermal downscaling
    therm = can_data.append(spec)
    i_therm = therm.downscale_region('i_therm', region = 'Canada', proxy = 'i_spec')
    rc_therm = therm.downscale_region('rc_therm', region = 'Canada', proxy = 'rc_spec')
    
    # Feedstock downscaling
    feed = can_data.append(spec)
    i_feed = feed.downscale_region('i_feed', region = 'Canada', proxy = 'i_spec')
    
    # Gather all data together
    total = spec
    total.append(can_data, inplace = True)
    total.append(i_therm, inplace = True)
    total.append(rc_therm, inplace = True)
    total.append(i_feed, inplace = True)
    
    # Change provinces names 
    total.rename(region = {'British Columbia': 'BritishColumbia',
                           'New Brunswick': 'NewBrunswick',
                           'Newfoundland and Labrador': 'NewfoundlandandLabrador',
                           'Northwest Territories': 'NorthwestTerritories',
                           'Nova Scotia': 'NovaScotia',
                           'Prince Edward Island': 'PrinceEdwardIsland'}, inplace = True)
    
    # Filter to required year range
    total = total.filter(year = MSG_YEARS)
    
    
    demand = total.timeseries()
    
    # Fill in 2055/2060 with growth rate from previous years
    demand[2055] = demand[2050]*demand[2050]/demand[2045]
    demand[2060] = demand[2055]*demand[2055]/demand[2050]
    
    # Sort dataframe
    demand = demand.reset_index()
    demand.drop(columns = ['scenario', 'model'], inplace = True)
    demand = demand.melt(id_vars = ['region', 'variable', 'unit'], var_name = 'year', value_name = 'value')
    demand = demand.set_index(['region', 'variable', 'year', 'unit']).sort_index().reset_index()


    # Return desired demand dataframe (National or Provincial)
    if scale == 'CAN':
        can_demand = demand[demand['region'] == 'Canada'].reset_index()
    
        can_dmd = make_df(
            'demand',
            node = can_demand['region'], 
            commodity = can_demand['variable'], 
            year = can_demand['year'], 
            time = 'year',
            level = 'useful',
            value = can_demand['value'], 
            unit = 'GWa')
        
        return can_dmd
    
    else: 
        prov_demand = demand[demand['region'] != 'Canada'].reset_index()
        
        prov_dmd = make_df(
            'demand',
            node = prov_demand['region'], 
            commodity = prov_demand['variable'], 
            year = prov_demand['year'], 
            time = 'year',
            level = 'useful',
            value = prov_demand['value'], 
            unit = 'GWa')
        
        return prov_dmd

# BELOW IS ALL FROM BEFORE 2020
# Read in data for feedstock
    #     # Read in data from csv
    #     i_feed = pd.read_csv(file)
        
    #     # Filter to only include feedstock data
    #     i_feed = i_feed[i_feed['Supply and demand characteristics'] == 'Non-energy use']
        
    #     # Format variable data
    #     i_feed['tech'] = i_feed['Supply and demand characteristics'] + '|' + i_feed['Fuel type']
    #     i_feed = i_feed[['year', 'node', 'tech', 'unit', 'VALUE']]
    #     i_feed['unit'] = 'TJ'
        
    #     # Create MESSAGE dataframe
    #     i_feed = pyam.IamDataFrame(i_feed, variable = 'tech', model = 'MESSAGEix', scenario = 'None', region = 'node', value = 'VALUE')
    #     i_feed = i_feed.aggregate('Non-energy use')
        
    #     # Rename to match MESSAGE variable name
    #     i_feed.rename(variable = {'Non-energy use': 'i_feed'}, inplace = True)
        
    #     return i_feed
    
    # if name == 'space_heating':
        
    #     space_heating = pd.read_excel(file)
        
    #     years = list(space_heating.columns.values[7:])
    #     space_heating = space_heating[['node', 'variable', 'unit'] + years]
    #     space_heating = pyam.IamDataFrame(space_heating, model = 'MESSAGEix', scenario = 'None', region = 'node')
        
    #     return space_heating