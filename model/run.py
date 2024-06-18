
import message_ix
import ixmp as ix
from ixmp import Scenario
from message_ix import make_df
from pre_process.format import format_demand
import pandas as pd
from pathlib import Path

# Stand-alone model
modelName = 'MESSAGEix_CA'      # A MESSAGE model name
scenarioName = 'baseline'       # A MESSAGE model scenario name
ssp = 'SSP1'

path = Path().cwd()

mp = ix.Platform()

# Creating a new MESSAGE stand-alone model
msg = message_ix.Scenario(mp, modelName, scenarioName,
                            version='new', annotation='')

# Path to data folder
DATA = Path().cwd().parent / 'data'

OUTPUT = Path().cwd().parent / 'output'

# Read in parameter data from previous MESSAGE run
msg.read_excel(DATA / 'MESSAGE_CA__test__v5.xlsx',
               add_units=False,
               commit_steps=False,
               init_items = True)

# Check out in order to add more data
msg.check_out()

# Create years variable for generating dataframes
years = [x for x in msg.set('year') if x >2015]

# growth_gas = growth[growth['technology'].str.contains('gas')]
# msg.remove_par('growth_activity_up', growth_gas)
# growth_gas['value'] = growth_gas['value'] * 0.5
# msg.add_par('growth_activity_up', growth_gas)
growth_gas_lo = msg.par('growth_activity_lo')
# growth_gas_lo = growth_gas_lo[(~growth_gas_lo['technology'].str.contains('gas_extr',regex= True))]
growth_gas_lo = growth_gas_lo[growth_gas_lo['technology'].str.contains('gas', regex=True)]
# growth_gas_lo = msg.par('growth_activity_lo')
# growth_gas_lo = growth_gas_lo[growth_gas_lo['technology'].str.contains('gas_extr')]
msg.remove_par('growth_activity_lo', growth_gas_lo)
growth_gas_lo['value'] = growth_gas_lo['value'] * 10
msg.add_par('growth_activity_lo', growth_gas_lo)
# %%
growth_gas_up = msg.par('growth_activity_up')
growth_gas_up = growth_gas_up[growth_gas_up['technology'].str.contains('gas', regex=True)]
gas_extr_2 = growth_gas_up[growth_gas_up['technology'] == 'gas_extr_2'].copy()
gas_extr_2['value'] = gas_extr_2['value'] * 1 / 100
msg.remove_par('growth_activity_up', gas_extr_2)
msg.add_par('growth_activity_up', gas_extr_2)
# %%
growth_gas_up = msg.par('growth_activity_up')

gas_extr_2 = growth_gas_up[growth_gas_up['technology'] == 'gas_extr_2'].copy()
gas_extr_2['value'] = gas_extr_2['value'] * 1 / 100
gas_extr_2['technology'] = 'gas_extr_1'
msg.add_par('growth_activity_up', gas_extr_2)

# %%
bound_gas = make_df('bound_activity_up',
                    node_loc='Canada',
                    technology='gas_extr_1',
                    year_act=years,
                    mode='M1',
                    time='year',
                    value=70,
                    unit='GWa')

bound_gas_1 = make_df('bound_activity_up',
                      node_loc='Canada',
                      technology='gas_extr_2',
                      year_act=years,
                      mode='M1',
                      time='year',
                      value=120,
                      unit='GWa')

bound_gas = pd.concat([bound_gas, bound_gas_1])

# %%
msg.add_par('bound_activity_up', bound_gas)
# %%
msg.add_par('bound_emission', ['Canada', 'TCE', 'all', 'cumulative'],
            value=600., unit='-')
# %%
msg.model
msg.version
msg.commit('')
# %%
# Exporting the built model (Scenario) to GAMS with an optional case name
caseName = msg.model + '__' + msg.scenario + '__v' + str(msg.version)

# Solving the model
msg.solve(model='MESSAGE', case=caseName)
# %%
# Save updated scenario to new excel sheet
msg.to_excel(path / 'data' / 'MESSAGE_CA__test__v5.xlsx')