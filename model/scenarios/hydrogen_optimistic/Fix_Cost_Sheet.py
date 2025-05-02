import pandas as pd
import os

# Define file paths
folder_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\data'
fix_cost_no_obps_path = os.path.join(folder_path, 'fix_cost_no_obps.csv')
model_default_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\model\scenarios\baseline\model_default_v23_GL.xlsx'

# Check if the file exists before trying to read it
if not os.path.exists(fix_cost_no_obps_path):
    print(f"The file {fix_cost_no_obps_path} does not exist.")
else:
    # Read the fix_cost_no_obps CSV file
    fix_cost_no_obps = pd.read_csv(fix_cost_no_obps_path)

    # Read the 'fix_cost' sheet from the model_default_v24 Excel file
    with pd.ExcelFile(model_default_path) as xls:
        model_default = pd.read_excel(xls, sheet_name='fix_cost')

    # Get the list of technologies in model_default
    existing_technologies = set(model_default['technology'])

    # Filter fix_cost_no_obps to include only technologies present in model_default
    filtered_fix_cost_no_obps = fix_cost_no_obps[fix_cost_no_obps['technology'].isin(existing_technologies)]

    # Save the filtered data to a new file
    output_path = os.path.join(folder_path, 'filtered_fix_cost_no_obps.xlsx')
    filtered_fix_cost_no_obps.to_excel(output_path, index=False)

    print(f"The filtered data has been written to {output_path}.")

