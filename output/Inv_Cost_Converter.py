import pandas as pd
import numpy as np

def convert_investment_costs():
    try:
        # Read both sheets from the excel file
        df_sheet3 = pd.read_excel('Inv_cost_high_LR.xlsx', sheet_name='Sheet3')
        
        # Get list of technologies from Sheet3
        technologies = df_sheet3['Tec'].unique()
        
        # List of provinces
        provinces = ['Alberta', 'BritishColumbia', 'Manitoba', 'NewBrunswick', 
                    'NewfoundlandandLabrador', 'NorthwestTerritories', 'NovaScotia',
                    'Nunavut', 'Ontario', 'PrinceEdwardIsland', 'Quebec', 
                    'Saskatchewan', 'Yukon']
        
        # Create year range with 5-year steps from 2020 to 2060
        years = list(range(2020, 2065, 5))
        
        # Create empty list to store new rows
        new_rows = []
        
        # For each technology in Sheet3
        for tech in technologies:
            tech_data = df_sheet3[df_sheet3['Tec'] == tech]
            
            # Get the year columns (assuming they are numeric column names)
            year_cols = [col for col in tech_data.columns if str(col).isdigit()]
            year_vals = tech_data[year_cols].values[0]
            
            # Create interpolation function for this technology
            year_indices = [int(year) for year in year_cols]
            interp_func = np.interp(years, year_indices, year_vals)
            
            # Create rows for each province and year
            for province in provinces:
                for i, year in enumerate(years):
                    new_row = {
                        'node_loc': province,
                        'technology': tech,
                        'year_vtg': year,
                        'value': round(float(interp_func[i]), 2),  # Round to 2 decimal places
                        'unit': 'USD/kW'
                    }
                    new_rows.append(new_row)
        
        # Create new dataframe from the rows
        new_df = pd.DataFrame(new_rows)
        
        # Sort the dataframe
        new_df = new_df.sort_values(['node_loc', 'technology', 'year_vtg'])
        
        # Save to excel file
        with pd.ExcelWriter('Inv_cost_high_LR.xlsx', engine='openpyxl', mode='a', 
                           if_sheet_exists='replace') as writer:
            new_df.to_excel(writer, sheet_name='Sheet1', index=False)
            
        print("Successfully converted and saved investment costs.")
        
    except FileNotFoundError:
        print("Error: The file 'Inv_cost_high_LR.xlsx' was not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    convert_investment_costs()