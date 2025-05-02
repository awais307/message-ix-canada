import pandas as pd
import pyam 

# Read the Excel file
#"C:\Users\brend\Documents\GitHub\message-ix - CA\reporting_outputs\MESSAGEix-CA_baseline_Muhammad.xlsx"
df = pd.read_excel('/Users/brend/Documents/GitHub/message-ix - CA/reporting_outputs/MESSAGEix-CA_baseline_2025-04-23--17-29.xlsx')

# Convert only the negative values in the columns from 2020 to 2060 to their absolute values
df.loc[:, 2025:2060] = df.loc[:, 2025:2060].abs()

# Drop rows where 'Region' is NaN
df = df.dropna(subset=['Region'])

# Remove duplicate rows
df = df.drop_duplicates(subset=['Model', 'Region', 'Scenario', 'Unit', 'Variable'])

# Now create the pyam.IamDataFrame
df_pyam = pyam.IamDataFrame(df)

# Convert back to pandas DataFrame
df = df_pyam.as_pandas()

# Ensure 'value' column is float
df['value'] = df['value'].astype(float)

# Set model name
df['model'] = 'MESSAGEix-Canada'

# Rename 'year' column to 'time'
df.rename(columns={'year':'time'}, inplace=True)

# Save to CSV
df.to_csv('/Users/brend/Documents/GitHub/message-ix - CA/reporting_outputs/output_neg_var_costs.csv')

