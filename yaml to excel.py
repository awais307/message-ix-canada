import yaml
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# Read the YAML file
with open('technology (1).yaml', 'r') as file:
    data = yaml.safe_load(file)

# Prepare the data for DataFrame
tech_data = []
for tech in data:
    tech_data.append({
        'technology': tech['technology'],
        'Description': tech['Description'],
        'Level': tech['Level'],
        'Input commodity/level': tech['Input commodity/level'],
        'Output commodity/level': tech['Output commodity/level'],
        'Tier': tech['Tier']
    })

# Create a DataFrame
df = pd.DataFrame(tech_data)

# Create a new workbook and select the active sheet
wb = Workbook()
ws = wb.active

# Write the DataFrame to the worksheet
for r in dataframe_to_rows(df, index=False, header=True):
    ws.append(r)

# Save the workbook
wb.save('technologies.xlsx')

print("Excel file 'technologies.xlsx' has been created successfully.")