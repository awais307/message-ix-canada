import pandas as pd
import os

# Define file paths
folder_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\data'
fix_cost_no_obps_path = os.path.join(folder_path, 'fix_cost_no_obps.csv')
model_default_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\model\scenarios\validation\model_default_v24.xlsx'

# Read the fix_cost_no_obps CSV file
fix_cost_no_obps = pd.read_csv(fix_cost_no_obps_path)

# Read all sheets from the model_default Excel file
with pd.ExcelFile(model_default_path) as xls:
    sheets = {sheet_name: pd.read_excel(xls, sheet_name=sheet_name) 
              for sheet_name in xls.sheet_names}

# Ensure the columns match between the two DataFrames
common_columns = list(set(fix_cost_no_obps.columns) & set(sheets['fix_cost'].columns))

# Get the list of technologies in model_default
existing_technologies = set(sheets['fix_cost']['technology'])

# Filter fix_cost_no_obps to only include existing technologies
fix_cost_no_obps_filtered = fix_cost_no_obps[fix_cost_no_obps['technology'].isin(existing_technologies)]

# Merge the DataFrames to update values
sheets['fix_cost'] = pd.merge(sheets['fix_cost'], fix_cost_no_obps_filtered[common_columns], 
                              on=['technology'], how='left', suffixes=('_old', '_new'))

# Update values in sheets['fix_cost']
for col in common_columns:
    if col != 'technology':
        sheets['fix_cost'][col] = sheets['fix_cost'][f'{col}_new'].fillna(sheets['fix_cost'][f'{col}_old'])

# Drop unnecessary columns
sheets['fix_cost'] = sheets['fix_cost'].drop([col + '_old' for col in common_columns if col != 'technology'], axis=1)
sheets['fix_cost'] = sheets['fix_cost'].drop([col + '_new' for col in common_columns if col != 'technology'], axis=1)

# Write all sheets back to the Excel file
with pd.ExcelWriter(model_default_path, engine='openpyxl', mode='w') as writer:
    for sheet_name, df in sheets.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print("The 'fix_cost' sheet in model_default_v24.xlsx has been updated successfully.")


