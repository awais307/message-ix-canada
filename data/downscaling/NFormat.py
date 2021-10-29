import pandas as pd
import pyam

# A function used to format demand data for MESSAGE
def NFormat(file, name):
    
    # Source == Canada's Energy Future
    if name == 'can_energy_future':
        
        # Read in data from excel file
        energy_future_data = pd.read_excel(file)
        
        # Extract time horizon
        years = [x for x in list(energy_future_data.columns.values) if x.startswith('2')]
        
        # Format variable data
        energy_future_data['variable'] = energy_future_data['Sector'] + '|' + energy_future_data['Variable']
        energy_future_data = energy_future_data[['node', 'variable', 'unit'] + years]
        energy_future_data['unit'] = 'PJ'
        
        # List of variable name changes
        energy_future_changes = {'Transportation|Total End-Use': 'transport',
                                 'Residential|Electricity': 'sp_el_r',
                                 'Commercial|Electricity': 'sp_el_c',
                                 'Residential|Biofuels & Emerging Energy': 'solar_pv_r',
                                 'Commercial|Biofuels & Emerging Energy': 'solar_pv_c',
                                 'Industrial|Electricity': 'sp_el_I',
                                 'Industrial|Biofuels & Emerging Energy': 'solar_pv_I'}

        entries = []

        # Add formatted variables to list to be used for statcan dataframe
        for x in range(0, len(energy_future_data)):
            if energy_future_data.at[x,'variable'] in list(energy_future_changes.keys()):
                energy_future_data.at[x,'variable'] = energy_future_changes[energy_future_data.at[x,'variable']]
                entry = energy_future_data.iloc[[x]].copy()
                entries.append(entry)
        
        # Create dataframe from list
        spec = pd.concat(entries, ignore_index = True)
        spec = pyam.IamDataFrame(spec, model = 'MESSAGEix', scenario = 'None', region = 'node')
        
        # Aggregate variables to get specific res/comm and tranport demands
        spec.add('solar_pv_r', 'solar_pv_c', 'solar_pv_rc', ignore_units = 'PJ', append = True)
        spec.add('sp_el_r', 'sp_el_c', 'sp_el_rc', ignore_units = 'PJ', append = True)
        spec.add('sp_el_rc', 'solar_pv_rc', 'rc_spec', ignore_units = 'PJ', append = True)
        spec.add('sp_el_I', 'solar_pv_I', 'i_spec', ignore_units = 'PJ', append = True)
        
        # Return only aggregated variables
        return spec.filter(variable = ['rc_spec', 'i_spec', 'transport'])
    
    if name == 'statcan':
        
        # Read in data from csv
        i_feed = pd.read_csv(file)
        
        # Filter to only include feedstock data
        i_feed = i_feed[i_feed['Supply and demand characteristics'] == 'Non-energy use']
        
        # Format variable data
        i_feed['tech'] = i_feed['Supply and demand characteristics'] + '|' + i_feed['Fuel type']
        i_feed = i_feed[['year', 'node', 'tech', 'unit', 'VALUE']]
        i_feed['unit'] = 'TJ'
        
        # Create MESSAGE dataframe
        i_feed = pyam.IamDataFrame(i_feed, variable = 'tech', model = 'MESSAGEix', scenario = 'None', region = 'node', value = 'VALUE')
        i_feed = i_feed.aggregate('Non-energy use')
        
        # Rename to match MESSAGE variable name
        i_feed.rename(variable = {'Non-energy use': 'i_feed'}, inplace = True)
        
        return i_feed
    
    if name == 'space_heating':
        
        space_heating = pd.read_excel(file)
        
        years = list(space_heating.columns.values[7:])
        space_heating = space_heating[['node', 'variable', 'unit'] + years]
        space_heating = pyam.IamDataFrame(space_heating, model = 'MESSAGEix', scenario = 'None', region = 'node')
        
        return space_heating
