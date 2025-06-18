import os
import pandas as pd

# Use raw string for the folder path
folder_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\data'


# Use os.path.join to create file paths
file_path_old = os.path.join(folder_path, 'Fix_cost_old .xlsx')
file_path_no_obps = os.path.join(folder_path, 'fix_cost_no_obps.xlsx')

fix_cost_old = pd.read_excel(file_path_old)
fix_cost_no_obps = pd.read_excel(file_path_no_obps)

# Set the index for both dataframes
index_columns = ['node_loc', 'technology', 'year_vtg', 'year_act']
fix_cost_old.set_index(index_columns, inplace=True)
fix_cost_no_obps.set_index(index_columns, inplace=True)

# Calculate the difference
fix_cost_difference = fix_cost_no_obps['value'] - fix_cost_old['value']

# Create a new dataframe with the difference
result = pd.DataFrame(fix_cost_difference, columns=['value'])
result['unit'] = fix_cost_old['unit']  # Assuming the unit remains the same

# Reset the index to include all columns
result.reset_index(inplace=True)

output_file_path = os.path.join(folder_path, 'fix_cost_difference.xlsx')
# Save the result to a new Excel file
result.to_excel(output_file_path, index=False)

print(f"Difference calculated and saved to {output_file_path}")
