import pandas as pd
import os

# Define file paths
folder_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\model\scenarios\baseline'
v22_path = os.path.join(folder_path, 'model_default_v22_fix_cost_updates.xlsx')
v23_path = os.path.join(folder_path, 'model_default_v23_GL.xlsx')

# Read the 'fix_cost' sheet from both Excel files
with pd.ExcelFile(v22_path) as xls:
    model_default_v22 = pd.read_excel(xls, sheet_name='fix_cost')

with pd.ExcelFile(v23_path) as xls:
    model_default_v23 = pd.read_excel(xls, sheet_name='fix_cost')

# Convert DataFrames to tuples for comparison
v22_rows = set(tuple(row) for row in model_default_v22.values.tolist())
v23_rows = set(tuple(row) for row in model_default_v23.values.tolist())

# Find rows in v23 but not in v22
rows_in_v23_not_in_v22 = list(v23_rows - v22_rows)

# Output the result
output_path = os.path.join(folder_path, 'rows_in_v23_not_in_v22.xlsx')
pd.DataFrame(rows_in_v23_not_in_v22, columns=model_default_v23.columns).to_excel(output_path, index=False)

print(f"The list of rows in v23 but not in v22 has been written to {output_path}.")

