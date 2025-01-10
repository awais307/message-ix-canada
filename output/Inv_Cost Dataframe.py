import pandas as pd

df = pd.read_excel(r"C:\Users\brend\Documents\GitHub\message-ix - CA\output\MESSAGEix-CA_baseline.xlsx", sheet_name='data')

# Create a copy of the filtered data with the exact Variable name
hydrogen_data = df[df['Variable'] == 'Investment|Energy Supply|Hydrogen'].copy()

# Sum the year columns after dividing by 100
year_columns = [2030, 2035, 2040, 2045, 2050]
hydrogen_data['value'] = hydrogen_data[year_columns].apply(lambda x: x/100).sum(axis=1)

# Create final dataframe with value and region
result_data = hydrogen_data[['value', 'Region']].rename(columns={'Region': 'region'})

# Save to Excel
result_data.to_excel('hydrogen_investment_sums.xlsx', index=False)

# Display results
print(result_data)