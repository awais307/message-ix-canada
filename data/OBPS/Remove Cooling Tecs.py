import pandas as pd
from openpyxl import load_workbook

# Define file path
file_path = r'C:\Users\brend\Documents\GitHub\message-ix - CA\model\scenarios\netzero\model_default_netzero_v7.xlsx'

# Read the fix_cost sheet
fix_cost_df = pd.read_excel(file_path, sheet_name='fix_cost')

# Define cooling terms to remove
cool_terms = ["__air", "__cl_fresh", "__ot_fresh", "__ot_saline"]

# Remove cooling technology rows
fix_cost_df = fix_cost_df[~fix_cost_df['technology'].str.contains('|'.join(cool_terms), na=False)]

# Save the updated DataFrame back to the Excel file
with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    fix_cost_df.to_excel(writer, sheet_name='fix_cost', index=False)

print("Cooling technologies have been removed from the fix_cost sheet.")


