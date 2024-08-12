# %% [markdown]
# ### Importing Modules

# %%
import message_ix
import ixmp as ix
import numpy as np
import pandas as pd
from ixmp import Scenario
from message_ix import make_df
from pre_process.prov_parameters import generator,remove_canada_data, remove_technology_data
from pathlib import Path
from pre_process.update_calibration import model_calibrate
from pre_process.update_units import unit_correction
from pre_process.cleanup_rel_tec import cleanup_rel_tec
from message_ix.report import Reporter
from message_ix.util import make_df

# from message_ix_models.util import (
#     broadcast, 
#     make_matched_dfs,
#     private_data_path,
#     same_node,
#     same_time,
# )

# %%
# Path to data folder
DATA = Path().cwd().parent / 'data'
TEST = Path().cwd().parent / 'test'

# %% [markdown]
# ## Initialize scenario

# %%
 # Stand-alone model
# Define the model and scenario names
modelName = 'MESSAGEix_CA_provincial'      # A MESSAGE model name
scenarioName = 'baseline_calibrated'       # A MESSAGE model scenario name
ssp = 'SSP2'

# connecting to the IX modeling platform - it can be defined as user defined playtform

mp = ix.Platform(name = 'default')

# here we create a scenario name to store the information of the model
# one can make any name technically, here we say it as msg , we can also say whatever we want e.g scenario etc. 
# version number mentions if there is alreay a scenario but if we read a scenario from excel file, we say it as 'new'
msg = message_ix.Scenario(mp, modelName, scenarioName,
                            version= 'new', annotation='')

# %%
# Read in data from Canadian scenario if the version number is not specified
# this is the simple command to read an excel file and store it in the scenario
# once loaded the scenario will have information
msg.read_excel(DATA / 'data_CA_provincial_reference_v1.xlsx',
               add_units=True, 
               commit_steps=False,
               init_items = True)

# %%
# # Clone Solved scenarios
## this is a process to clone a scenario 
## this is not needed everytime but if we have a scenario which is already solved and we want to clone it to make some changes or 
# create a new scenario with different changed 
## note that line 9 is basically the new scenario namme, which can go into config file 
scen1 = msg.clone(
    modelName,
    "netzero_pathway",
    "Adding historical data",
    keep_solution=False,
)



# %%
## every time you need to make changes in the model, you need to check out the scenario
## consider check_out command as opening a scenario 
scen1.check_out()

# %%
# this is not needed right now or in the main script but if we want to add some historical data to the model
# we can simply do that using the following command which is ready the exceil file and adding it to the model

df = pd.read_excel(DATA / 'historical_activity.xlsx')
scen.add_par('historical_activity', df)

# %%
### Note that this historical data assumes that Ridley's script is already run and the data is coorec in the excel file
# but the workflow should be available that we run the file and adjust the values

# %%
## this script reads in the population raw data and processes it to be used in the model
## the data is read in from the folder and processed it 
## this doesn't need to be run everytime but need to go in a separate function so everytime we have to reproudce and update population 


data = pd.read_csv(DATA / 'pop_gdp_process/population_predictions_MG1.csv')
# Step 2: Rename 'Unnamed: 0' to 'Year' and convert 'Year' to datetime
data.rename(columns={'Unnamed: 0': 'Year'}, inplace=True)
data['Year'] = pd.to_datetime(data['Year'], format='%Y')

# Step 3: Pivot the dataframe to long format
pivoted_data = data.melt(id_vars=['Year'], var_name='Province', value_name='Population')

# Step 4: Set 'Year' as index and sort the index
pivoted_data.set_index('Year', inplace=True)
pivoted_data.sort_index(inplace=True)

# Step 5: Forward fill and backward fill to handle missing values
pivoted_data['Population'] = pivoted_data['Population'].ffill().bfill()

# Step 6: Resample and interpolate
resampled_data = pivoted_data.groupby('Province').resample('5A').mean().interpolate(method='linear')

# Step 7: Reset the index to have 'Year' as a column again
resampled_data = resampled_data.reset_index()

# Change the datetime format to the required format (e.g., 2020, 2025, etc.)

# Update the year values to the required format
resampled_data['Year'] = resampled_data['Year'].dt.year - 1

df_pop = resampled_data
df_pop['Province'] = df_pop['Province'].str.replace(' ', '')
# this simply converts it back to the model required format
df_pop.to_csv(DATA / 'gdp_messageca_prov.csv', index=False)

# %%
## same for GDP - both can go in the same function 

df_gdp = pd.read_csv(DATA / 'pop_gdp_process/SSP_GDP_Projections.csv')

# Pivot the dataframe to have years under a single column named 'Year'
gdp_data = df_gdp.melt(id_vars=['prov'], var_name='Year', value_name='GDP')

# Rename the columns for clarity
gdp_data.rename(columns={'prov': 'Province'}, inplace=True)


gdp_data['Province'] = gdp_data['Province'].str.replace(' ', '')



# %%
gdp_data.to_csv(DATA / 'pop_gdp_process/gdp_messageca_prov.csv', index=False)

# %%
df_pop_1 = df_pop.copy()
df_pop_1.rename(columns={'Population': 'value', 'Province': 'node_loc', 'Year': 'year_act'}, inplace=True)
df_pop_1['technology'] = 'Population'
df_pop_1['mode'] = 'P'
df_pop_1['time'] = 'year'
df_pop_1['unit'] = 'GWa/a'

df_gdp_1 = gdp_data.copy()
df_gdp_1.rename(columns={'GDP': 'value', 'Province': 'node_loc', 'Year': 'year_act'}, inplace=True)
df_gdp_1['technology'] = 'GDP'
df_gdp_1['mode'] = 'P'
df_gdp_1['time'] = 'year'
df_gdp_1['unit'] = 'GWa/a'

concatenated_df_socio= pd.concat([df_pop_1, df_gdp_1])

df = scen.par('bound_activity_lo')

df_filtered = df[~df['technology'].isin(['Population', 'GDP'])]

df_bound_new = pd.concat([df_filtered, concatenated_df_socio])



# %%
## adds population and gdp to the scenario 
## this can go in the same function

scen.check_out()
scen.add_par('bound_activity_lo', df_bound_new)



# %% [markdown]
# ### every time we add some parameters to scenario, we check out and then commit. if we checkout  then we need to commit too. if we checkout two times, the scenario will be locked. 

# %% [markdown]
# ## now the script is to adjust the demands. this all can go in a separate function for demands. There are some functions for the demands already, Ideally we can change that but if it sounds dififcult we can create the workflow below into a function. 

# %%
df_population = pd.read_csv(DATA / 'pop_gdp_process/population_data.csv')

# %%
scen.commit('Added population and gdp bounds')

# %%
# Get the time parameters
first_year = scen.set('cat_year').loc[msg.set(
        'cat_year')['type_year'] == 'firstmodelyear', 'year'].item()
msg_yrs = [int(x) for x in scen.set('year')]
hist_year = 2015
demand_yrs = [x for x in msg_yrs if x >= hist_year]

# %%
df_demand = scen.par('demand')
hist_act_df = scen.par('historical_activity')

# %%
hist_act_df.to_csv(DATA / 'historical_activity.csv', index=False)

# %%
df_dem.to_csv(DATA / 'demand.csv', index=False)

# %%
tec_list = list(set((msg.par(
                        'output', {'level':'useful',
                                   'commodity': 'transport'}))['technology']))

# filter historical activity datafrme to include technologies for current commodity
if(len(tec_list)>1):
    ha = hist_act_df.loc[hist_act_df.technology.isin(tec_list)]
else:
    ha = hist_act_df.loc[hist_act_df['technology'] == tec_list[0]]

# %%
# Adjusting the GDP and population part of the script
ssp_gdp_df = pd.read_csv(DATA / 'pop_gdp_process/gdp_messageca_prov.csv')
ssp_pop_df = pd.read_csv(DATA / 'pop_gdp_process/pop_messageca_prov.csv')
ssp_pop_df['Population'] = ssp_pop_df['Population'] * 1000
ssp_pop_df['Province'] = ssp_pop_df['Province'].str.replace(' ', '')

# Adjusting province names for consistency
province_mapping = {
    'Newfoundland and Labrador': 'NewfoundlandandLabrador',
    'Prince Edward Island': 'PrinceEdwardIsland'
}
ssp_pop_df['Province'] = ssp_pop_df['Province'].replace(province_mapping)

# List of provinces from the data
provinces = ssp_gdp_df['Province'].unique()

ssp_df = []
for province in provinces:
    c_ssp_gdp_df = ssp_gdp_df.loc[ssp_gdp_df.Province == province]
    c_ssp_pop_df = ssp_pop_df.loc[ssp_pop_df.Province == province]
    gdp = []
    pop = []
    gdpc = []

    for jjj in [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]:
        if not c_ssp_gdp_df.loc[c_ssp_gdp_df.Year == jjj].empty and not c_ssp_pop_df.loc[c_ssp_pop_df.Year == jjj].empty:
            gdp.append(c_ssp_gdp_df.loc[c_ssp_gdp_df.Year == jjj, 'GDP'].values[0])
            pop.append(c_ssp_pop_df.loc[c_ssp_pop_df.Year == jjj, 'Population'].values[0])
            gdpc.append(gdp[-1] / pop[-1])
        else:
            gdp.append(np.nan)
            pop.append(np.nan)
            gdpc.append(np.nan)

    ssp_df.append(pd.DataFrame({
        'year': [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060],
        'gdp': gdp,
        'pop': pop,
        'gdpc': gdpc,
        'iso': province
    }))

ssp_df = pd.concat(ssp_df)

ssp_df.head()


# %%
provinces

# %%
ssp_pop_df.Province.unique()

# %%
ssp_pop_df[ssp_pop_df['Province'] == 'BritishColumbia']

# %%
# Summing the demand across nodes
df_region = df_demand.groupby(['year', 'commodity','level','time','unit']).sum().reset_index()

# %%
df_region['node'] = 'Canada'

# %%

df_dem = df_region
cmdtys = df_dem['commodity'].unique().tolist()


# %%
df_region.to_csv(DATA / 'cad_demand.csv', index=False)
# for percentage change 

# %%
cmdtys

# %%
from pre_process.downscale_demands import downscale_demands

# %%
iso = 'Canada'

# %%
df_region

# %%
dff.level.values[0]

# %%
# List of technologies outputting on the demand level
tec_list = list(set((scen.par('output', {'level': dff.level.values[0], 'commodity': cmdtys}))['technology']))


# %%
tec_list

# %%
ssp_df

# %%
cmdtys

# %%
import pandas as pd
import numpy as np

# Initial dictionary for demand data
dmds_dict = {}

# Go through each demand commodity and update demands then add to df above
for cmdty in cmdtys:
    for province in ssp_df['iso'].unique():
        print(f"Processing province: {province}")  # Debugging
        province_df = ssp_df[ssp_df['iso'] == province]

        # Isolate regional demands
        dff = df_region[df_region['commodity'] == cmdty].sort_values('year').reset_index(drop=True)

        # Use dff as basis for province df so update node location
        dff['node'] = province

        # Add percent change
        dff['pc'] = dff['value'].pct_change(periods=1)
        dff = dff.replace([np.inf, -np.inf, np.nan], 0)

        # List of technologies outputting on the demand level
        tec_list = list(set((scen.par('output', {'level': dff.level.values[0], 'commodity': cmdty}))['technology']))

        # Filter historical activity dataframe to include technologies for current commodity
        if len(tec_list) > 1:
            ha = hist_act_df.loc[hist_act_df.technology.isin(tec_list)]
        else:
            ha = hist_act_df.loc[hist_act_df['technology'] == tec_list[0]]

        # Ensure 'value' columns are numeric
        ha['value'] = pd.to_numeric(ha['value'], errors='coerce')

        # Filter historical activity for the current province
        ha = ha[ha['node_loc'].str.strip().replace(" ", "") == province.strip().replace(" ", "")]

        # Debugging: Check data after merging and calculating 'value'
        print("Data types of 'ha' after merging and calculating 'value':")
        print(ha.dtypes)
        print(ha.head())

        # Initialize the provincial demand values for the first year
        initial_demand = ha.loc[ha['year_act'] == demand_yrs[0]].groupby('node_loc')['value'].sum().reset_index()
        initial_demand_value = initial_demand['value'].sum() if not initial_demand.empty else 0
        dff.loc[dff['year'] == demand_yrs[1], 'value'] = initial_demand_value

        # # Go through each demand year and scale the historical demands to follow regional growth pattern
        # # Must be sorted by year because the state equations are updated sequentially
        for ind in range(1, len(dff)):

        #     # Apply the percentage change to update demands for subsequent years
            dff.loc[ind, 'value'] = dff.loc[ind - 1, 'value'] * (1 + dff.loc[ind, 'pc'])

        #     # Debugging
            print('--- cmdty ---')
            print(cmdty)

            print('--- province ---')
            print(province)

        #     print('--- dff ---')
            print(dff)

        # Store the demand for the current province and commodity in the dictionary
        if cmdty not in dmds_dict:
            dmds_dict[cmdty] = []
        dmds_dict[cmdty].append(dff.copy())

# Combine the results into a single DataFrame
demand_df = pd.concat([pd.concat(dmds_dict[cmdty], ignore_index=True) for cmdty in dmds_dict], ignore_index=True)


# %%
demand_df

# %%
import pandas as pd
import numpy as np

# Initial df for demand data
dmds = []

# Go through each demand commodity and update demands then add to df above
for cmdty in cmdtys:
    for province in ssp_df['iso'].unique():
        print(f"Processing province: {province}")  # Debugging
        province_df = ssp_df[ssp_df['iso'] == province]

        # Isolate regional demands
        dff = df_region[df_region['commodity'] == cmdty].sort_values('year').reset_index(drop=True)

        # Use dff as basis for province df so update node location
        dff['node'] = province

        # Add percent change
        dff['pc'] = dff['value'].pct_change(periods=1)
        dff = dff.replace([np.inf, -np.inf, np.nan], 0)

        # List of technologies outputting on the demand level
        tec_list = list(set((scen.par('output', {'level': dff.level.values[0], 'commodity': cmdty}))['technology']))

        # Filter historical activity dataframe to include technologies for current commodity
        if len(tec_list) > 1:
            ha = hist_act_df.loc[hist_act_df.technology.isin(tec_list)]
        else:
            ha = hist_act_df.loc[hist_act_df['technology'] == tec_list[0]]

        # Ensure 'value' columns are numeric
        ha.loc[:, 'value'] = pd.to_numeric(ha['value'], errors='coerce')

        # Filter historical activity for the current province
        ha = ha[ha['node_loc'].str.strip().replace(" ", "") == province.strip().replace(" ", "")]

        # Debugging: Check data after merging and calculating 'value'
        print("Data types of 'ha' after merging and calculating 'value':")
        print(ha.dtypes)
        print(ha.head())

        # Go through each demand year and scale the historical demands to follow regional growth pattern
        # Must be sorted by year because the state equations are updated sequentially
        for ind in dff.index:

            # If the first year, use the historical demands calibrated to iea db
            if dff.year.iloc[ind] == demand_yrs[0]:

                # Sum iea demands
                dm = ha.loc[ha['year_act'] == dff.year.iloc[ind]].groupby('node_loc').sum().reset_index()
                dm = dm[['node_loc', 'value']]

                dt = dm['value'].sum()

                # Update the demand value for the province
                dff.loc[ind, 'value'] = dt

            # For subsequent years, apply the percentage change to update demands
            else:

                # Update total provincial demands using growth rate from previous year
                dff.loc[ind, 'value'] = dff['value'].iloc[ind - 1] * (1 + dff['pc'].iloc[ind])

            # Check
            print('--- cmdty ---')
            print(cmdty)

            print('--- province ---')
            print(province)

            print('--- dff ---')
            print(dff)

        # Add demand for particular commodity to the model
        dmds.append(dff[list(msg.par('demand').columns)])

# %%
dff

# %%
initial_demand

# %%
df.to_excel(DATA / 'historical_activity.xlsx', index=False)

# %%
def downscale_demands( target, initial, income_i, income_f, gdp_f, names ):
    
    # Aim is to minimize the maximum difference between the percent change 
    # in per capits GDP and energy intensity (per unit GDP).
    #
    # This is the LP problem:
    #
    # Min:  alpha
    # s.t.  alpha >= | phi_c - delta_c | forall c
    #       sum_c(beta_c*delta_c) = target - sum_c(beta_c)
    #       alpha >= 0
    
    # # don't allow 0 intensities in future time steps
    # ei = initial / income_i
    # ei[np.where(ei==0)] =  min(ei[ei.nonzero()])
    # initial = ei * income_i
    
    # the above simplifying parameters defined as:
    beta = income_f * initial / income_i
    phi = income_f / income_i - 1
    
    # x = [alpha, delta_1, delta_2, ...., delta_n]    
    # LP objective function coefficients for minimizing maximum difference in growth rates
    cobj = [1]
    cobj.extend([0]*len(names))
    cobj = np.array(cobj)

    # maxmin abs value constraint upper bound 1
    a = np.array([-1]*len(names))
    a.shape=(len(names),1)
    b = np.identity(len(names))
    Aub1 = np.concatenate((a,b),axis=1)
    bub1 = phi
    bub1.shape = (len(names),1)
    
    # maxmin abs value constraint upper bound 2
    a = np.array([-1]*len(names))
    a.shape=(len(names),1)
    b = np.identity(len(names))
    b *= -1
    Aub2 = np.concatenate((a,b),axis=1)
    bub2 = -1*phi
    bub2.shape = (len(names),1)
    
    # non negativity for absolute value
    Aub3 = np.array([-1])
    Aub3 = np.append(Aub3,[0]*len(names))
    Aub3.shape = (1,(len(names)+1))
    bub3 = np.array([[0]])
    Aub = np.concatenate((Aub1,Aub2,Aub3),axis=0)
    bub = np.concatenate((bub1,bub2,bub3),axis=0)

    # Equality constraint for ensuring the country balances match the regional target
    Aeq = np.array(np.append([0],beta))
    Aeq.shape = (1,(1+len(names)))
    beq = np.array([[target-sum(beta)]])
    beq.shape = (1,1)

    # Call LP solver
    res = linprog(
        c = cobj,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=beq,
        bounds=(-np.inf, np.inf),
        options={"disp":True,"tol":3.6e-10})
        
    # Return data frame with updated parameters
    val = []
    for i in range(1,(len(names)+1)):
        val.append(income_f[i-1]*(initial[i-1]/income_i[i-1])*(1+res.x[i]))
    
    df = pd.DataFrame({'node':names,'value':val})
    return df

# %%
initial_demand_value = initial_demand['value'].sum() if not initial_demand.empty else 0


# %%
initial_demand_value

# %%
demand_df

# %%
scen.add_par('demand', demand_df)

# %% [markdown]
# ## Solve Model
# 
# The following piece is used to solve the model.

# %%
# Exporting the built model (Scenario) to GAMS with an optional case name
# Case name is defined so the output file name is suitable and appropriate version to identify later. 
caseName = scen.model + '__' + scen.scenario + '__v' + str(scen.version)
scen.model
scen.version
scen.commit('')

# %%
# Solving the model
scen.solve(solve_options={'barcrossalg': '2','lpmethod':'1'}, case=caseName)


# %%
# if solved or even if it is not solved, the user wants to conver the scenario to excel file, this command is used. 
scen1.to_excel('data_CA_provincial_netzero_carbon_price_v1.xlsx')

# %% [markdown]
# ## Demand Reduction

# %%
## this is a demand reduction script, can be converted into a separate function and called when needed

# %%
data = msg.par('demand')

# %%
data1= data

# %%
import pandas as pd


# Loop through each unique combination of node and commodity
nodes = data['node'].unique()
commodities = data['commodity'].unique()

# Define the reduction factors for the key years
reduction_factors = {
    2020: 1.0,    # No reduction in 2020
    2050: 0.78,   # 18% reduction by 2050
    2060: 0.8    # 20% reduction by 2060
}

# Create a function to calculate the reduction factor for any given year
def calculate_reduction_factor(year):
    if year in reduction_factors:
        return reduction_factors[year]
    else:
        # Linear interpolation
        if year < 2050:
            return 1.0 + (0.82 - 1.0) * (year - 2020) / (2050 - 2020)
        else:
            return 0.82 + (0.80 - 0.82) * (year - 2050) / (2060 - 2050)

# Function to apply reduction
def apply_reduction(group):
    for index, row in group.iterrows():
        year = row['year']
        reduction_factor = calculate_reduction_factor(year)
        group.at[index, 'value'] = row['value'] * reduction_factor
    return group

# Apply the reduction to each combination of node and commodity
for node in nodes:
    for commodity in commodities:
        mask = (data['node'] == node) & (data['commodity'] == commodity)
        data.loc[mask] = apply_reduction(data.loc[mask])



# Display the first few rows of the modified data
data.head(10)


# %%
data.to_csv('demands.csv')

# %%
data1.to_csv('demands_baseline.csv')

# %%
scen1.add_par('demand', data)

# %%
scen1.check_out()

# %%
df = scen1.par('bound_emission')

# %%
df['value'] = df['value']/5

# %%
scen1.commit('')

# %%
scen1.check_out()

# %%


# %% [markdown]
# ## Balanced 2050 Pathway - Net Zero Scenario
# 
# This is an example for the net zero pathway and used to colone

# %%
# # Clone Solved scenarios
scen2 = scen1.clone(
    modelName,
    "netzero_pathway",
    "Adding historical data",
    keep_solution=False,
)


# %%
scen2.check_out()

# %%
df_fix = pd.read_csv(DATA / 'updated_obps_NetZero_fix_cost.csv')

# %%
scen2.add_par('fix_cost',df_fix)

# %% [markdown]
# ### Net Zero Emissions

# %%
import pandas as pd

# Load the Excel file
file_path = DATA / 'emissions_trajectory.xlsx'  # Update with your file path
sheet_names = pd.ExcelFile(file_path).sheet_names

# Load the sheets
sheet1 = pd.read_excel(file_path, sheet_name='Sheet1')
sheet2 = pd.read_excel(file_path, sheet_name='Sheet2')

# Define the percentage reductions and the corresponding years
reduction_schedule = {
    2025: -16.69195751,
    2030: -33.38391502,
    2035: -50.07587253,
    2040: -66.61608498,
    2045: -68,
    2050: -70,
    2055: -70,
    2060: -70
    }

# Extract the unique provinces (nodes)
provinces = sheet2['node'].unique()

# Initialize a list to store the emission trajectories for each province
emission_trajectories_list = []

# Iterate over each province and apply the reduction schedule
for province in provinces:
    # Extract the emission data for the province
    province_data = sheet2[sheet2['node'] == province]
    
    # Create a dictionary to store the year and emission values
    province_emissions = {'province': [], 'year': [], 'emission': []}
    
    # Iterate over the reduction schedule and calculate the emissions
    for year, reduction in reduction_schedule.items():
        # Get the base year emission value (we'll use the earliest available year's emission as the base)
        if year in province_data['type_year'].values:
            base_year_emission = province_data[province_data['type_year'] == year]['value'].values[0]
            # Calculate the emission value for the current year
            emission_value = base_year_emission * (1 + reduction / 100)
            # Store the emission value in the dictionary
            province_emissions['province'].append(province)
            province_emissions['year'].append(year)
            province_emissions['emission'].append(emission_value)
    
    # Convert the dictionary to a DataFrame and append to the list
    province_emissions_df = pd.DataFrame(province_emissions)
    emission_trajectories_list.append(province_emissions_df)

# Concatenate all the DataFrames into a single DataFrame
emission_trajectories_df = pd.concat(emission_trajectories_list).reset_index(drop=True)

# Save the resulting DataFrame to a new Excel file
output_file_path = DATA / 'emission_trajectories_netzero.xlsx'  # Update with your desired output file path
emission_trajectories_df.to_excel(output_file_path, index=False)

print(emission_trajectories_df)


# %%

emission_trajectories_df


# %%
emission_trajectories_df.rename(columns={
    'province': 'node',
    'year': 'type_year',
    'emission': 'value'
}, inplace=True)


# %%
emission_trajectories_df['type_tec'] = 'all'
emission_trajectories_df['type_emission'] = 'TCE'
emission_trajectories_df['unit'] = '-'


# %%
scen1.check_out()

# %%
scen1.add_par('bound_emission',emission_trajectories_df )

# %%
df = scen2.par('bound_emission')

# %%
scen2.check_out()

# %%
scen2.remove_par('bound_emission', df)

# %%
    

# %%
df = df[df['node']!= 'Canada']

# %%
df

# %%
scen2.add_par('bound_emission', df)

# %%
scen2.add_par(
    "bound_emission",
    make_df(
        "bound_emission",
        node='Canada',
        type_emission="TCE",
        type_tec="all",
        type_year= [2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060],
        value=[
            659000000,
            549000000,
            439000000,
            329000000,
            220000000,
            110000000,
            110000000,
            110000000,
        ],
        unit="tCO2",
    ),
)


# %% [markdown]
# ## Reporting

# %%
## now is reporting basically  postprocessing the outputs using appropriate computations. 
# Ridley already learnt about the reporting using tutotiral, but below is the script to report the model outputs in the format we require

# %%
## This code is bascially what we need to convert th emodel output to the csv and then this csv can b
# read in in IDEA.
unit_correct = True  # unit s must be corrected to run this script
from_excel = False
min_year = 2015
max_year = 2060
from_excel = False
#%% Generating reporter
rep = Reporter.from_scenario(msg, units={"apply": {"var_cost": "","inv_cost": "", "fix_cost": ""}})
report = rep.get('message::default') # in fact, only in = input x ACT, out = output x ACT is needed

if from_excel:
    # Read default report
    report_df = pd.read_csv('MESSAGE_NO_example_default_report.csv')
else:
# Or if trying another country model, execute the next 4:
    report_df = report.timeseries()
    report_df.reset_index(inplace=True)
    report_df.columns = report_df.columns.astype(str)
    report_df.columns = report_df.columns.str.title()
    
report_df = report.timeseries()
report_df.reset_index(inplace=True)
report_df.columns = report_df.columns.astype(str)
report_df.columns = report_df.columns.str.title()
# Plotted years
years = msg.set('year').tolist()
years = [str(x) for x in years if x >= min_year and x <= max_year]

# Create data for Sankey diagrams and plot it using plotly
report_df.fillna(0, inplace = True)

# Convert from GWa to TWh (*8.76)
# c = report_df.select_dtypes(include=[np.number]) * 8.76
# report_df[c.columns] = c

# Drop not necessary years
report_df.columns = report_df.columns.astype(str)
report_df = report_df.drop(report_df.columns.to_series()['2020': str(min_year)],
                           axis=1)

# Identify input and output variables and its flows (provided within the Reporter: in = input x ACT, out = output x ACT)
in_flows = report_df[report_df['Variable'].str.startswith("in|")]
out_flows = report_df[report_df['Variable'].str.startswith("out|")]
all_flows = pd.concat([out_flows , in_flows])
report_df['Model'] = 'MESSAGEix-Canada'
report_df['Scenario'] = 'Reference'
report_df["Variable"] = report_df["Variable"].str.replace('emis', 'Emissions', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('total om cost|', 'Total Costs|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP_NEW|new capacity|', 'Capacity Addition|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('inv cost|', 'Capital Cost|', regex = False)
report_df['Region'] = report_df['Region'].apply(lambda x: x.split('|')[0])
import pyam
import matplotlib.pyplot as plt
import pyam
plotyrs = [2020,2025,2030,2035,2040,2045,2050,2055,2060]
pyam_df = pyam.IamDataFrame(report_df)
variable = pyam_df.variable
pyam_df.aggregate_region(variable, append = True)
pyam_df.rename({'region': {'World': 'Canada'}}, inplace=True)
pdf = pyam_df.copy()
pdf.to_csv('MESSAGE_CANADA_provincial_baseline_v1.csv')


# %%
## every time we complete, its important to close the database connection 
mp.close_db()

# %%


# %%


# %%


# %%


# %%


# %%


# %%
len(pyam_df.region)

# %%
pyam_df.region

# %%


# %%


# %%


# %%


# %%
df = pd.read_csv('MESSAGE_CANADA_provincial_baseline_v1.csv')

# %%
df_1 = pd.read_csv('MESSAGE_CANADA_provincial_high_tech_v1.csv')

# %%
df = pd.concat([df,df_1])

# %%


# %%
df = pd.read_csv('MESSAGE_CANADA_provincial_reference_v1.csv')

# %%

biomass = ['Primary Energy|biomass|bio_istig_ccs|M1', 
'Primary Energy|biomass|bio_istig|M1'
'Primary Energy|biomass|bio_ppl|M1',
'Primary Energy|biomass|biomass_nc|M1',
'Primary Energy|biomass|biomass_t_d|M1',
'Primary Energy|biomass|eth_bio_ccs|M1',
'Primary Energy|biomass|eth_bio|M1',
'Primary Energy|biomass|gas_bio|M1',
'Primary Energy|biomass|h2_bio_ccs|M1',
'Primary Energy|biomass|h2_bio|M1',
'Primary Energy|biomass|liq_bio_ccs|M1',
'Primary Energy|biomass|liq_bio|M1',
'Primary Energy|biomass|land_use_biomass|M1',
]

lng = ['Primary Energy|LNG|LNG_bal|M1']

coal = ['Primary Energy|coal|coal_bal|M1',
                      'Primary Energy|coal|coal_exp|M1',
                      'Primary Energy|coal|coal_exp|M1',
                      'Primary Energy|coal|coal_extr_ch4|M1',
                      'Primary Energy|coal|coal_extr|M1',
                      'Primary Energy|coal|lignite_extr|M1']

gas = ['Primary Energy|gas|gas_bal|M1',
    'Primary Energy|gas|gas_extr_1|M1',
      'Primary Energy|gas|gas_extr_2|M1',
      'Primary Energy|gas|gas_extr_3|M1',
      'Primary Energy|gas|gas_extr_4|M1',
      'Primary Energy|gas|gas_extr_5|M1',
      'Primary Energy|gas|gas_extr_6|M1',
      'Primary Energy|gas|LNG_prod|M1',
       'Primary Energy|LNG|LNG_bal|M1']

oil = ['Primary Energy|crudeoil|oil_bal|M1',
    'Primary Energy|crudeoil|oil_exp|M1',
     'Primary Energy|crudeoil|oil_extr_1_ch4|M1',
        'Primary Energy|crudeoil|oil_extr_1|M1',
        'Primary Energy|crudeoil|oil_extr_2_ch4|M1',
        'Primary Energy|crudeoil|oil_extr_2|M1',
        'Primary Energy|crudeoil|oil_extr_3_ch4|M1',
        'Primary Energy|crudeoil|oil_extr_3|M1',
        'Primary Energy|crudeoil|oil_extr_4_ch4|M1',
        'Primary Energy|crudeoil|oil_extr_4|M1',
        'Primary Energy|crudeoil|oil_extr_5|M1',
        'Primary Energy|crudeoil|oil_extr_6|M1',
        'Primary Energy|crudeoil|oil_extr_7|M1']

hydro = ['Primary Energy|renewable|hydro|hydro_hc|M1',  'Primary Energy|renewable|hydro|hydro_lc|M1']

biomass_renew = ['Primary Energy|renewable|biomass|bio_extr_a|M1',
                'Primary Energy|renewable|biomass|bio_extr_b|M1',
                'Primary Energy|renewable|biomass|bio_extr_c|M1',
                'Primary Energy|renewable|biomass|bio_extr_d|M1',
                'Primary Energy|renewable|biomass|bio_extr_e|M1',
                'Primary Energy|renewable|biomass|bio_extr_f|M1',
                'Primary Energy|renewable|biomass|bio_extr_g|M1']

solar = ['Primary Energy|renewable|solar_pv|solar_pv_ppl|M1' , 
         'Primary Energy|renewable|solar_th|solar_th_ppl|M1']


wind = ['Primary Energy|renewable|wind|wind_ppf|M1', 'Primary Energy|renewable|wind|wind_ppl|M1']

lh2 = ['Primary Energy|lh2|lh2_bal|M1', 'Primary Energy|lh2|lh2_exp|M1']

ethanol = ['Primary Energy|methanol|meth_bal|M1',  'Primary Energy|methanol|meth_exp|M1']

methanol = ['Primary Energy|ethanol|eth_bal|M1', 'Primary Energy|ethanol|eth_exp|M1']



# %%
pdf.aggregate(
    "Primary Energy|coal",
    components=coal,
    append=True
)


pdf.aggregate(
    "Primary Energy|renewable|solar",
    components=solar,
    append=True
)

pdf.aggregate(
    "Primary Energy|renewable|hydro",
    components=hydro,
    append=True
)

pdf.aggregate(
    "Primary Energy|ethanol",
    components=ethanol,
    append=True
)
pdf.aggregate(
    "Primary Energy|methanol",
    components=methanol,
    append=True
)
pdf.aggregate(
    "Primary Energy|Liq. Hydrogen",
    components=lh2,
    append=True
)
pdf.aggregate(
    "Primary Energy|renewable|wind",
    components=wind,
    append=True
)

pdf.aggregate(
    "Primary Energy|renewable|biomass",
    components= biomass_renew,
    append=True
)


pdf.aggregate(
    "Primary Energy|biomass",
    components= biomass,
    append=True
)

pdf.aggregate(
    "Primary Energy|oil",
    components=oil,
    append=True
)

pdf.aggregate(
    "Primary Energy|gas",
    components=gas,
    append=True
)

pdf.aggregate(
    "Primary Energy|LNG",
    components=lng,
    append=True
)

# %%
pdf.filter(variable = 'Primary Energy|gas').timeseries()

# %%
data.timeseries()

# %%
data.to_csv('primaryenergy.csv')

# %%
data = pdf.filter( variable=["Primary Energy|renewable|solar",
                                            "Primary Energy|LNG",
                                            "Primary Energy|gas",
                                            "Primary Energy|oil",
                                            "Primary Energy|biomass",
                                            "Primary Energy|renewable|wind",
                                            "Primary Energy|Liq. Hydrogen",
                                            "Primary Energy|methanol",
                                            "Primary Energy|ethanol",
                                            "Primary Energy|renewable|hydro",
                                            "Primary Energy|renewable|biomass",
                                            "Primary Energy|methanol",
                                           "Primary Energy|coal"],
              year = plotyrs, region = 'Canada')

data.plot.stack(title = 'Primary Energy by fuel - Baseline Scenario')
plt.legend(loc=1)
plt.tight_layout()
plt.show()

# %%
i_feed = ['Useful Energy|i_feed|ethanol_fs|M1', 'Useful Energy|i_feed|gas_fs|M1',
         'Useful Energy|i_feed|loil_fs|M1', 'Useful Energy|i_feed|methanol_fs|M1']

transport = ['Useful Energy|transport|coal_trp|M1',
            'Useful Energy|transport|elec_trp|M1',
            'Useful Energy|transport|eth_fc_trp|M1',
            'Useful Energy|transport|eth_ic_trp|M1',
            'Useful Energy|transport|foil_trp|M1',
            'Useful Energy|transport|gas_trp|M1',
            'Useful Energy|transport|h2_fc_trp|M1',
            'Useful Energy|transport|loil_trp|M1',
            'Useful Energy|transport|meth_fc_trp|M1',
            'Useful Energy|transport|meth_ic_trp|M1']


i_spec = ['Useful Energy|i_spec|h2_fc_I|M1',
          'Useful Energy|i_spec|sp_coal_I|M1',
          'Useful Energy|i_spec|sp_el_I|M1',
          'Useful Energy|i_spec|sp_eth_I|M1',
          'Useful Energy|i_spec|sp_liq_I|M1',
          'Useful Energy|i_spec|sp_meth_I|M1']

i_therm =   ['Useful Energy|i_therm|biomass_i|M1',
            'Useful Energy|i_therm|coal_i|M1',
            'Useful Energy|i_therm|elec_i|M1',
            'Useful Energy|i_therm|eth_i|M1',
            'Useful Energy|i_therm|foil_i|M1',
            'Useful Energy|i_therm|gas_i|M1',
            'Useful Energy|i_therm|h2_fc_I|M1',
            'Useful Energy|i_therm|h2_i|M1',
            'Useful Energy|i_therm|heat_i|M1',
            'Useful Energy|i_therm|hp_el_i|M1',
            'Useful Energy|i_therm|hp_gas_i|M1',
            'Useful Energy|i_therm|loil_i|M1',
            'Useful Energy|i_therm|meth_i|M1',
            'Useful Energy|i_therm|solar_i|M1']
rc_spec = ['Useful Energy|rc_spec|h2_fc_RC|M1',
          'Useful Energy|rc_spec|sp_el_RC|M1']

rc_therm = ['Useful Energy|rc_therm|biomass_rc|M1',
            'Useful Energy|rc_therm|coal_rc|M1',
            'Useful Energy|rc_therm|eth_rc|M1',
            'Useful Energy|rc_therm|foil_rc|M1',
            'Useful Energy|rc_therm|gas_rc|M1',
            'Useful Energy|rc_therm|h2_fc_RC|M1',
            'Useful Energy|rc_therm|h2_rc|M1',
            'Useful Energy|rc_therm|heat_rc|M1',
            'Useful Energy|rc_therm|hp_el_rc|M1',
            'Useful Energy|rc_therm|hp_gas_rc|M1',
            'Useful Energy|rc_therm|loil_rc|M1',
            'Useful Energy|rc_therm|meth_rc|M1',
            'Useful Energy|rc_therm|solar_rc|M1']

biom = ['Useful Energy|non-comm|biomass_nc|M1']

# %%
df_useful = pyam_df.copy()
# df_useful.aggregate(
#     "Useful Energy|non-Commercial biomass",
#     components=biom,
#     append=True
# )

df_useful.aggregate(
    "residential/commercial thermal",
    components=rc_therm,
    append=True
)

df_useful.aggregate(
    "residential/commercial specific",
    components=rc_spec,
    append=True
)

df_useful.aggregate(
    "industrial thermal",
    components=i_therm,
    append=True
)

df_useful.aggregate(
    "industrial specific",
    components=i_spec,
    append=True
)

df_useful.aggregate(
    "industrial feedstock",
    components=i_feed,
    append=True
)

df_useful.aggregate(
    "transport",
    components=i_therm,
    append=True
)


# %%
data = df_useful.filter( variable=[
    "non-Commercial biomass",
    "residential/commercial thermal",
    "residential/commercial specific",
    "industrial thermal",
    "industrial specific",
    "industrial feedstock",
    "transport"],
              year = plotyrs, region = 'BritishColumbia')


data.plot.stack(title = 'Demands by sector (British Columbia)', legend={"loc": "outside right"})
plt.legend(loc=1)
plt.tight_layout()
plt.show()

# %%
cement = ['Emissions|CO2|cement_CO2|M1']
coal = ['Emissions|CO2|coal_extr_ch4|M1',
        'Emissions|CO2|coal_extr|M1',
        'Emissions|CO2|coal_imp|M1']
foil = ['Emissions|CO2|foil_imp|M1']
gas = ['Emissions|CO2|gas_extr_1|M1',
        'Emissions|CO2|gas_extr_2|M1',
        'Emissions|CO2|gas_extr_3|M1',
        'Emissions|CO2|gas_extr_4|M1',
        'Emissions|CO2|gas_extr_5|M1',
        'Emissions|CO2|gas_extr_6|M1'
        ]
lignite = ['Emissions|CO2|lignite_extr|M1']
loil = ['Emissions|CO2|loil_imp|M1']
meth_ccs = ['Emissions|CO2|meth_coal_ccs|M1']
oil = ['Emissions|CO2|oil_extr_1_ch4|M1',
    'Emissions|CO2|oil_extr_1|M1',
    'Emissions|CO2|oil_extr_2_ch4|M1',
    'Emissions|CO2|oil_extr_2|M1',
    'Emissions|CO2|oil_extr_3_ch4|M1',
    'Emissions|CO2|oil_extr_3|M1',
    'Emissions|CO2|oil_extr_4_ch4|M1',
    'Emissions|CO2|oil_extr_4|M1',
    'Emissions|CO2|oil_extr_5|M1',
    'Emissions|CO2|oil_extr_6|M1',
    'Emissions|CO2|oil_extr_7|M1']

oil_trade = ['Emissions|CO2|foil_imp|M1',
             'Emissions|CO2|loil_exp|M1',
            'Emissions|CO2|loil_imp|M1',
             'Emissions|CO2|oil_imp|M1']
       
gas_trade = ['Emissions|CO2|LNG_exp|M1',
            'Emissions|CO2|LNG_imp|M1',
            'Emissions|CO2|gas_imp|M1']
            #'Emissions|CO2|LNG_exp|M1']

# %%
df_emis_b = pyam_df.filter(variable = 'Emissions|CO2|*',year = plotyrs)

# %%
df_emis_b.to_csv('emissions.csv')

# %%
df_emis = pyam_df.copy()


df_emis.aggregate(
    "Emissions|CO2|gas",
    components=gas,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|oil",
    components=oil,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|coal",
    components=coal,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|cement",
    components=cement,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|oil trade",
    components=oil_trade,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|gas trade",
    components=gas_trade,
    append=True
)

# %%
data = df_emis.filter( variable=
    ["Emissions|CO2|gas",
    "Emissions|CO2|oil",
    "Emissions|CO2|coal",
    "Emissions|CO2|cement"],
    # "Emissions|CO2|oil trade",
    # "Emissions|CO2|gas trade"],
              year = plotyrs, region = 'Canada')

data.plot.stack(title = 'CO2 Emissions - Baseline Scenario')
plt.legend(loc=1)
plt.tight_layout()
plt.show()

# %%
df_emis.aggregate('Emissions|*').timeseries()

# %%

coal = ['Total Costs|coal_adv',
        'Total Costs|coal_adv_ccs',
        'Total Costs|coal_bal',
        'Total Costs|coal_exp',
        'Total Costs|coal_extr',
        'Total Costs|coal_extr_ch4',
        'Total Costs|coal_gas',
        'Total Costs|coal_hpl',
        'Total Costs|coal_i',
        'Total Costs|coal_imp',
        'Total Costs|coal_ppl',
        'Total Costs|coal_ppl_u',
        'Total Costs|coal_rc',
        'Total Costs|coal_ppl',
        'Total Costs|coal_ppl_u',
       'Total Costs|coal_t_d',
       'Total Costs|syn_liq',
        'Total Costs|meth_coal',
       'Total Costs|lignite_extr']
biomass = ['bio_hpl', 'bio_ppl',
          'Total Costs|liq_bio']


elec = ['Total Costs|elec_exp',
        'Total Costs|elec_i',
        'Total Costs|elec_imp',
        'Total Costs|elec_t_d',
        'Total Costs|elec_trp']

oil = ['Total Costs|foil_i',
    'Total Costs|foil_imp',
    'Total Costs|foil_ppl',
    'Total Costs|oil_extr_1'
    'Total Costs|oil_extr_1_ch4'
    'Total Costs|oil_extr_2',
    'Total Costs|oil_extr_3',
    'Total Costs|oil_extr_4',
    'Total Costs|oil_extr_5',
    'Total Costs|oil_extr_6',
    'Total Costs|oil_extr_7',
    'Total Costs|oil_extr_2_ch4',
    'Total Costs|oil_extr_3_ch4',
    'Total Costs|loil_cc',
    'Total Costs|loil_ppl']
gas = ['Total Costs|gas_bal',
    'Total Costs|gas_bio',
    'Total Costs|gas_cc',
    'Total Costs|gas_cc_ccs',
    'Total Costs|gas_ct',
    'Total Costs|gas_extr_1',
    'Total Costs|gas_extr_2',
    'Total Costs|gas_extr_3',
    'Total Costs|gas_extr_4',
    'Total Costs|gas_extr_5',
    'Total Costs|gas_extr_6',
    'Total Costs|gas_extr_mpen',
    'Total Costs|gas_fs',
    'Total Costs|gas_hpl',
    'Total Costs|gas_i',
    'Total Costs|gas_imp',
    'Total Costs|gas_ppl',
    'Total Costs|gas_rc',
    'Total Costs|gas_t_d',
    'Total Costs|gas_t_d_ch4',
    'Total Costs|gas_trp',
      'Total Costs|igcc']

geo_ppl = ['Total Costs|geo_hpl','Total Costs|geo_ppl']

solar = ['Total Costs|solar_i',
        'Total Costs|solar_pv_ppl',
        'Total Costs|solar_rc',
        'Total Costs|solar_th_ppl']

wind = ['Total Costs|wind_curtailment1',
'Total Costs|wind_curtailment2',
'Total Costs|wind_curtailment3',
'Total Costs|wind_ppf',
'Total Costs|wind_ppl']

hydro = ['Total Costs|hydro_hc',
'Total Costs|hydro_lc']

nuclear = ['Total Costs|nuc_lc']


# %%
df_cost = pyam_df.copy()


df_cost.aggregate(
    "Total Costs|coal",
    components=coal,
    append=True
)

df_cost.aggregate(
    "Total Costs|biomass",
    components=biomass,
    append=True
)

df_cost.aggregate(
    "Total Costs|electricity",
    components=elec,
    append=True
)

df_cost.aggregate(
    "Total Costs|oil",
    components=biomass,
    append=True
)

df_cost.aggregate(
    "Total Costs|gas",
    components=gas,
    append=True
)

df_cost.aggregate(
    "Total Costs|geothermal",
    components=geo_ppl,
    append=True
)

df_cost.aggregate(
    "Total Costs|solar",
    components=solar,
    append=True
)

df_cost.aggregate(
    "Total Costs|wind",
    components=wind,
    append=True
)

df_cost.aggregate(
    "Total Costs|hydro",
    components=hydro,
    append=True
)
df_cost.aggregate(
    "Total Costs|nuclear",
    components=nuclear,
    append=True
)

# %%
data.unit

# %%


# %%
df_cost.timeseries()

# %%
data = df_cost.filter( variable=
    ["Total Costs|coal","Total Costs|biomass",
    # "Total Costs|electricity",
    "Total Costs|oil",
    "Total Costs|gas",
    "Total Costs|geothermal",
    "Total Costs|solar",
    "Total Costs|wind",
    "Total Costs|hydro",
    "Total Costs|nuclear"],
              year = plotyrs, region = 'Canada')
data.convert_unit("", to="million USD/yr", factor=0.000001, inplace = True)

data.plot.stack(title = 'Total (Operational+ Investment) Costs - High Tech Cost')
plt.legend(loc=1)
plt.ylabel('Million USD 2020/yr')
plt.tight_layout()

plt.show()


# %% [markdown]
# Now making another scenario cloned from baseline to add other policies. 
# 
# Policy No. 1
# Baseline - NDC 
# Implement Canada's commitments 
# 

# %%


# %%


# %%
technologies = [
    # "hp_el_rc",
    # "hp_gas_rc",
    # "hp_el_i",
    # "hp_gas_i",
    # "solar_pv_RC",
    # "solar_curtailment1",
    # "solar_cv1",
    "solar_pv_ppl",
    # "solar_res1",
    "solar_th_ppl",
    # "csp_sm3_res",
    # "csp_sm3_ppl",
    # "csp_sm1_res",
    # "csp_sm1_ppl",
    # "wind_curtailment1",
    "wind_cv1",
    "wind_ppl",
    "wind_res1",
    "wind_ppf",
    "wind_ref1",
    "stor_ppl",
    "h2_elec",
    "h2_smr_ccs",
    "bio_istig_ccs",
    "h2_mix",
    "glb_lh2_imp",
    "h2_bio_ccs",
    "h2_co2_scrub",
    "h2_coal",
    "h2_coal_ccs",
    "h2_liq",
    "h2_smr",
    "h2_t/d",
    "h2b_co2_scrub",
    # "lh2_bal",
    "lh2_exp",
    "lh2_imp",
    "lh2_regas",
    "lh2_t/d",
    # "h2_i",
    # "h2_fc_I",
    # "h2_rc",
    # "h2_fc_RC",
    # "h2_fc_trp",
    "LH2_bunker",
    "coal_adv_ccs",
    "gas_cc_ccs",
    "igcc_ccs",
    "cement_co2scr",
    "eth_bio_ccs",
    "liq_bio_ccs",
    "meth_coal_ccs",
    "meth_ng_ccs",
    "syn_liq_ccs",
    "cfc_co2scr"
]


# %%
msgbas = scen1.clone(modelName, 'netzero_low_cost',
                     keep_solution=False)
df_inv = msgbas.par('inv_cost')
df_var = msgbas.par('var_cost')
df_fix = msgbas.par('fix_cost')
df_inv.loc[df_inv['technology'].isin(technologies), 'value'] *=0.9
df_var.loc[df_var['technology'].isin(technologies), 'value'] *=0.9
df_fix.loc[df_fix['technology'].isin(technologies), 'value'] *=0.9

msgbas.check_out()
msgbas.add_par('inv_cost', df_inv)
msgbas.add_par('fix_cost', df_fix)
msgbas.add_par('var_cost', df_var)
msgbas.commit('Decreasing costs of innovative techs by 10%')
# Exporting the built model (Scenario) to GAMS with an optional case name
caseName = msgbas.model + '__' + msgbas.scenario + '__v' + str(msgbas.version)
msgbas.solve(model='MESSAGE', case=caseName, solve_options={'lpmethod': '4'})

# %%

unit_correct = True  # unit s must be corrected to run this script
from_excel = False
min_year = 2015
max_year = 2060
from_excel = False
#%% Generating reporter
rep = Reporter.from_scenario(msgbas, units={"apply": {"var_cost": "","inv_cost": "", "fix_cost": ""}})
report = rep.get('message::default') # in fact, only in = input x ACT, out = output x ACT is needed

if from_excel:
    # Read default report
    report_df = pd.read_csv('MESSAGE_NO_example_default_report.csv')
else:
# Or if trying another country model, execute the next 4:
    report_df = report.timeseries()
    report_df.reset_index(inplace=True)
    report_df.columns = report_df.columns.astype(str)
    report_df.columns = report_df.columns.str.title()
    
report_df = report.timeseries()
report_df.reset_index(inplace=True)
report_df.columns = report_df.columns.astype(str)
report_df.columns = report_df.columns.str.title()
# Plotted years
years = msg.set('year').tolist()
years = [str(x) for x in years if x >= min_year and x <= max_year]

# Create data for Sankey diagrams and plot it using plotly
report_df.fillna(0, inplace = True)

# Convert from GWa to TWh (*8.76)
# c = report_df.select_dtypes(include=[np.number]) * 8.76
# report_df[c.columns] = c

# Drop not necessary years
report_df.columns = report_df.columns.astype(str)
report_df = report_df.drop(report_df.columns.to_series()['2020': str(min_year)],
                           axis=1)

# Identify input and output variables and its flows (provided within the Reporter: in = input x ACT, out = output x ACT)
in_flows = report_df[report_df['Variable'].str.startswith("in|")]
out_flows = report_df[report_df['Variable'].str.startswith("out|")]
all_flows = pd.concat([out_flows , in_flows])
report_df['Model'] = 'MESSAGEix-Canada'
report_df['Scenario'] = 'Net Zero'
report_df["Variable"] = report_df["Variable"].str.replace('emis', 'Emissions', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('total om cost|', 'Total Costs|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP_NEW|new capacity|', 'Capacity Addition|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('inv cost|', 'Capital Cost|', regex = False)
report_df['Region'] = report_df['Region'].apply(lambda x: x.split('|')[0])
import pyam
import matplotlib.pyplot as plt
import pyam
plotyrs = [2020,2025,2030,2035,2040,2045,2050,2055,2060]
pyam_df = pyam.IamDataFrame(report_df)
variable = pyam_df.variable
pyam_df.aggregate_region(variable, append = True)
pyam_df.rename({'region': {'World': 'Canada'}}, inplace=True)
pdf = pyam_df.copy()
pdf.to_csv('MESSAGE_CANADA_provincial_netzero_lowcost_v1.csv')


# %%
msghigh = scen1.clone(modelName, 'netzero_high_cost',
                     keep_solution=False)
df_inv = msghigh.par('inv_cost')
df_var = msghigh.par('var_cost')
df_fix = msghigh.par('fix_cost')
df_inv.loc[df_inv['technology'].isin(technologies), 'value'] *=1.1
df_var.loc[df_var['technology'].isin(technologies), 'value'] *=1.1
df_fix.loc[df_fix['technology'].isin(technologies), 'value'] *=1.1

msghigh.check_out()
msghigh.add_par('inv_cost', df_inv)
msghigh.add_par('fix_cost', df_fix)
msghigh.add_par('var_cost', df_var)
msghigh.commit('Decreasing costs of innovative techs by 10%')
# Exporting the built model (Scenario) to GAMS with an optional case name
caseName = msghigh.model + '__' + msghigh.scenario + '__v' + str(msghigh.version)
msghigh.solve(model='MESSAGE', case=caseName, solve_options={'lpmethod': '4'})

# %%

unit_correct = True  # unit s must be corrected to run this script
from_excel = False
min_year = 2015
max_year = 2060
from_excel = False
#%% Generating reporter
rep = Reporter.from_scenario(msghigh, units={"apply": {"var_cost": "","inv_cost": "", "fix_cost": ""}})
report = rep.get('message::default') # in fact, only in = input x ACT, out = output x ACT is needed

if from_excel:
    # Read default report
    report_df = pd.read_csv('MESSAGE_NO_example_default_report.csv')
else:
# Or if trying another country model, execute the next 4:
    report_df = report.timeseries()
    report_df.reset_index(inplace=True)
    report_df.columns = report_df.columns.astype(str)
    report_df.columns = report_df.columns.str.title()
    
report_df = report.timeseries()
report_df.reset_index(inplace=True)
report_df.columns = report_df.columns.astype(str)
report_df.columns = report_df.columns.str.title()
# Plotted years
years = msg.set('year').tolist()
years = [str(x) for x in years if x >= min_year and x <= max_year]

# Create data for Sankey diagrams and plot it using plotly
report_df.fillna(0, inplace = True)

# Convert from GWa to TWh (*8.76)
# c = report_df.select_dtypes(include=[np.number]) * 8.76
# report_df[c.columns] = c

# Drop not necessary years
report_df.columns = report_df.columns.astype(str)
report_df = report_df.drop(report_df.columns.to_series()['2020': str(min_year)],
                           axis=1)

# Identify input and output variables and its flows (provided within the Reporter: in = input x ACT, out = output x ACT)
in_flows = report_df[report_df['Variable'].str.startswith("in|")]
out_flows = report_df[report_df['Variable'].str.startswith("out|")]
all_flows = pd.concat([out_flows , in_flows])
report_df['Model'] = 'MESSAGEix-Canada'
report_df['Scenario'] = 'Net Zero'
report_df["Variable"] = report_df["Variable"].str.replace('emis', 'Emissions', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|final|', 'Final Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|primary|', 'Primary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|secondary|', 'Secondary Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|renewable|', 'Primary Energy|renewable|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('total om cost|', 'Total Costs|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('out|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('in|useful|', 'Useful Energy|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP_NEW|new capacity|', 'Capacity Addition|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('CAP|capacity|', 'Capacity|', regex = False)
report_df["Variable"] = report_df["Variable"].str.replace('inv cost|', 'Capital Cost|', regex = False)
report_df['Region'] = report_df['Region'].apply(lambda x: x.split('|')[0])
import pyam
import matplotlib.pyplot as plt
import pyam
plotyrs = [2020,2025,2030,2035,2040,2045,2050,2055,2060]
pyam_df = pyam.IamDataFrame(report_df)
variable = pyam_df.variable
pyam_df.aggregate_region(variable, append = True)
pyam_df.rename({'region': {'World': 'Canada'}}, inplace=True)
pdf = pyam_df.copy()
pdf.to_csv('MESSAGE_CANADA_provincial_netzero_highcost_v1.csv')


# %%
pdf.aggregate(
    "Primary Energy|coal",
    components=coal,
    append=True
)


pdf.aggregate(
    "Primary Energy|renewable|solar",
    components=solar,
    append=True
)

pdf.aggregate(
    "Primary Energy|renewable|hydro",
    components=hydro,
    append=True
)

pdf.aggregate(
    "Primary Energy|ethanol",
    components=ethanol,
    append=True
)
pdf.aggregate(
    "Primary Energy|methanol",
    components=methanol,
    append=True
)
pdf.aggregate(
    "Primary Energy|Liq. Hydrogen",
    components=lh2,
    append=True
)
pdf.aggregate(
    "Primary Energy|renewable|wind",
    components=wind,
    append=True
)

pdf.aggregate(
    "Primary Energy|renewable|biomass",
    components= biomass_renew,
    append=True
)


pdf.aggregate(
    "Primary Energy|biomass",
    components= biomass,
    append=True
)

pdf.aggregate(
    "Primary Energy|oil",
    components=oil,
    append=True
)

pdf.aggregate(
    "Primary Energy|gas",
    components=gas,
    append=True
)

pdf.aggregate(
    "Primary Energy|LNG",
    components=lng,
    append=True
)

# %%
pdf.filter(variable = 'Primary Energy|oil').timeseries()

# %%


# %%
pdf.filter( variable=["Primary Energy|renewable|solar",
                                            #"Primary Energy|LNG",
                                            "Primary Energy|gas",
                                            "Primary Energy|oil",
                                            "Primary Energy|biomass",
                                            "Primary Energy|renewable|wind",
                                            "Primary Energy|Liq. Hydrogen",
                                            "Primary Energy|methanol",
                                            "Primary Energy|ethanol",
                                            "Primary Energy|renewable|hydro",
                                            "Primary Energy|renewable|biomass",
                                            "Primary Energy|methanol",
                                           "Primary Energy|coal"],
              year = plotyrs).stack_plot(total=True,
                                        title = 'Primary Energy by fuel - Baseline Scenario')

# %%
df_emis = pyam_df.copy()


df_emis.aggregate(
    "Emissions|CO2|gas",
    components=gas,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|oil",
    components=oil,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|coal",
    components=coal,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|cement",
    components=cement,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|oil trade",
    components=oil_trade,
    append=True
)

df_emis.aggregate(
    "Emissions|CO2|gas trade",
    components=gas_trade,
    append=True
)

# %%
df_emis.timeseries()

# %%
df_emis.filter( variable=
    ["Emissions|CO2|gas",
    "Emissions|CO2|oil",
    "Emissions|CO2|coal",
    "Emissions|CO2|cement",
    "Emissions|CO2|oil trade",
    "Emissions|CO2|gas trade"],
              year = plotyrs,region = 'Canada').stack_plot(total=True,
                                         title = 'CO2 Emissions - Baseline Scenario')

# %%
import pandas as pd

# %%
df = pd.read_csv('MESSAGE_CANADA_baselinendc.csv')

# %%
df['Model'].replace('CD_Links_SSP2_R14', 'MESSAGEix-Canada', inplace=True)

# %%
df.head()

# %%
df.to_csv('MESSAGE_CANADA_v1.csv')

# %%
import pandas as pd

# %%
iso = 'CAN'

# %%
# SSP GDP data
ssp_gdp_df = pd.read_excel( str('OECD_SSP_GDP_PPP.xlsx'),
        'OECD_SSP_GDP_PPP',
        header = 0)
ssp_gdp_df = ssp_gdp_df.loc[ (  ssp_gdp_df.Region == iso ) ].reset_index(drop=True)

# SSP population data

ssp_pop_df = pd.read_excel(str('OECD_SSP_POP.xlsx'),
        'OECD_SSP_POP',
        header = 0)
ssp_pop_df = ssp_pop_df.loc[ (  ssp_pop_df.Region == iso  ) ].reset_index(drop=True)

# %%
ssp_pop_df['Scenario'] = ssp_pop_df['Scenario'].str.replace('_v9_130325', '')
ssp_gdp_df['Scenario'] = ssp_gdp_df['Scenario'].str.replace('_v9_130325', '')

# %%
ssp_gdp_df

# %%
import pyam
import matplotlib.pyplot as plt
import pyam

pop_df = pyam.IamDataFrame(ssp_pop_df)
gdp_df = pyam.IamDataFrame(ssp_gdp_df)

# %%
pop_df.head()

# %%
pop_df.plot(color='scenario', title='Population Projections of Canada across SSPs')

# %%
gdp_df.plot(color='scenario', title='GDP Projections of Canada across SSPs')

# %%
mp.add_unit('tCO2/kWa')
mp.add_unit('MtCO2')

# %%
msgbas.set('type_emission')

# %%

msgbas.add_par('bound_emission', ['Canada', 'TCE', 'all', 'cumulative'],
             value=700., unit='MtCO2')

# %%
msgbas.commit('adding emissions bound')

# %%
msgbas.solve()

# %%
msgbas.scenario

# %%
msgbas.par('bound_emission')

# %%
msgCT = msgbas.clone(modelName, 'carbon_bound_by_year','introducing a carbon tax',
                             keep_solution=False)
msgCT.check_out()

# %%
emissions = msgCT.var('EMISS')
emissions

# %%

emission_prices_by_year = msg.var('PRICE_EMISSION')
emission_prices_by_year

# %%

scen_tax = base.clone(model, 'carbon_tax','introducing a carbon tax',
                      keep_solution=False)
scen_tax.check_out()

# %%
years

# %%

base_tax_emission = {
    'node': 'Canada',
    'type_year': years,
    'type_tec': 'all',
    'unit': 'USD/tCO2',
    'type_emission': 'GHG',
    'value': emission_prices.set_index('year').lvl
}

# %%


# in case you need to add the new unit to the platform
mp.add_unit('USD/tCO2')

tax_emission = make_df(base_tax_emission)
scen_tax.add_par('tax_emission', tax_emission)
scen_tax.par('tax_emission')

# %%

scen_tax.commit(comment='setting taxes on emissions')

# %%
scen_tax.var('EMISS', {'node': 'Westeros'})


