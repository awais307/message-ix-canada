
'''

The following code creates an excel file that allows users investigate results via:
    - A total Contributions sheet that aggregates data for each region and year across all end-use variables of interest.
    - Detailed values sheets that provide detailed year-by-year data for each variable of interest, with sheet names truncated to fit Excel's 31-character limit.
    - A specific variable contributions sheet for both a region of interest and the nation which shows total contributions for specific end-use variables on a sector.

Define specific_variables, end_use_Variables or prefixes, and specific_region

'''

import pandas as pd

# Load the result dataset
file_path = r"C:\Users\brend\Documents\GitHub\message-ix - CA\MESSAGEix_CA__hydrogen_share__v63func_test.csv"
df = pd.read_csv(file_path)

# Define variables of interest. This is the denominator of the ratio of variables in a total share.
end_use_variables = [
    "in|final|hydrogen|h2_fc_RC|M1", "in|final|hydrogen|h2_rc|M1", 
    "in|final|coal|coal_rc|M1", "in|final|biomass|biomass_rc|M1", 
    "in|final|d_heat|heat_rc|M1", "in|final|electr|elec_rc|M1", 
    "in|final|electr|hp_el_rc|M1", "in|final|electr|sp_el_RC|M1", 
    "in|final|ethanol|eth_rc|M1", "in|final|fueloil|foil_rc|M1", 
    "in|final|gas|gas_rc|M1", "in|final|gas|hp_gas_rc|M1", 
    "in|final|lightoil|loil_rc|M1", "in|final|methanol|meth_rc|M1"
]

filtered_df = df[df['Variable'].isin(end_use_variables)]

# If you wish to define variables of interest based on prefixes, uncomment out the following two lines of code and comment out above.
#prefixes = ["in|primary", "in|secondary"]
#filtered_df = df[df['Variable'].apply(lambda x: any(x.startswith(prefix) for prefix in prefixes))]

#print (filtered_df)

# Define the years of interest
years = ['2025', '2030', '2035', '2040', '2045', '2050', '2055', '2060']

total_end_use_sums = {year: filtered_df[year].sum() for year in years}

region_contributions = filtered_df.groupby('Region').sum().reset_index()
region_contributions = region_contributions[['Region'] + years]

sheets = {'Total Contributions': region_contributions}

detailed_values = []
for variable in end_use_variables:
    variable_df = df[df['Variable'] == variable]
    
    if not variable_df.empty:
        variable_df = variable_df[['Region'] + years]
        variable_df.set_index('Region', inplace=True)
        
        # Truncate the variable name for the Excel sheet name to 31 characters
        sheet_name = f'{variable[:30]}'  # Adjusting length to ensure it fits
        detailed_values.append((sheet_name, variable_df.reset_index()))

for sheet_name, data in detailed_values:
    sheets[sheet_name] = data

# Calculate specific contributions for a region of interest. This specific_variables variable is your numerator for share in the region of interest and the overall nation.
specific_region = 'BritishColumbia|BritishColumbia'
specific_variables = ["in|final|hydrogen|h2_fc_RC|M1", "in|final|hydrogen|h2_rc|M1"]

specific_sums = {year: 0 for year in years}
specific_end_use_sums = {year: 0 for year in years}

for specific_variable in specific_variables:
    specific_df = df[(df['Variable'] == specific_variable) & (df['Region'] == specific_region)]
    if not specific_df.empty:
        for year in years:
            specific_sums[year] += specific_df[year].sum()

for year in years:
    specific_end_use_sums[year] = df[(df['Region'] == specific_region) & (df['Variable'].isin(end_use_variables))][year].sum()

specific_percentage_df = pd.DataFrame({
    'Year': years,
    'Specific Contribution': [specific_sums[year] for year in years],
    'Specific End Use Sum': [specific_end_use_sums[year] for year in years],
    'Percentage': [100 * specific_sums[year] / specific_end_use_sums[year] if specific_end_use_sums[year] > 0 else 0 for year in years]
})
sheets['BC Contribution %'] = specific_percentage_df.set_index('Year')

all_regions_sums = {year: 0 for year in years}

for specific_variable in specific_variables:
    specific_df = df[df['Variable'] == specific_variable]
    for year in years:
        all_regions_sums[year] += specific_df[year].sum()

all_regions_percentage_df = pd.DataFrame({
    'Year': years,
    'Total Contribution Across All Regions': [all_regions_sums[year] for year in years],
    'Total End Use Sum': [total_end_use_sums[year] for year in years],
    'Percentage': [100 * all_regions_sums[year] / total_end_use_sums[year] if total_end_use_sums[year] > 0 else 0 for year in years]
})
sheets['All Regions Contribution %'] = all_regions_percentage_df.set_index('Year')

# Write all data to an Excel file
output_file = r"C:\Users\brend\Documents\GitHub\message-ix - CA\MESSAGEix_CA__hydrogen_share__results.xlsx"
with pd.ExcelWriter(output_file) as writer:
    for sheet_name, sheet_data in sheets.items():
        sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Results have been written to {output_file}")
