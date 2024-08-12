import pandas as pd
import numpy as np
import os
import xlrd as xl
import csv


technologies_extr = ['gas_extr_mpen', 'oil_extr_mpen', 'coal_extr_mpen']
technologies_exp = ['oil_exp', 'gas_exp', 'coal_exp']

def adjust_export_values(df, tech_extr_mpen, tech_exp):
    for location in df['node_loc'].unique():
        # Extract rows for the current location and year 2015
        loc_data = df[(df['node_loc'] == location) & (df['year_act'] == 2015)]
        # Check if both required technologies exist in the location data
        if tech_extr_mpen in loc_data['technology'].values and tech_exp in loc_data['technology'].values:
            extr_mpen_val = loc_data.loc[loc_data['technology'] == tech_extr_mpen, 'value'].values[0]
            exp_val = loc_data.loc[loc_data['technology'] == tech_exp, 'value'].values[0]
            # Adjust export value if it's greater than extraction minus penalties value
            if exp_val > extr_mpen_val:
                df.loc[(df['node_loc'] == location) & (df['technology'] == tech_exp) & (df['year_act'] == 2015), 'value'] = 0.7 * extr_mpen_val
    return df

def supply_balance(production, imports, exports, demand):
    imports = demand - production
    exports = demand - 2 * imports
    balance = bool (production == (imports + exports))
    return balance

def downscale(parameter, scaler):
    return parameter * scaler

# Function by Stack Overflow user Parvathirajan Natarajan
# Source: https://stackoverflow.com/a/62619543
def write_excel(filename,sheetname,dataframe):
    with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer: 
        workBook = writer.book
        try:
            workBook.remove(workBook[sheetname])
        except:
            print("Worksheet does not exist")
        finally:
            dataframe.to_excel(writer, sheet_name=sheetname,index=False)
            writer.save()

def compare_validate(production_file, imp_exp_file, demand_file):
    validate_prod = pd.read_excel(production_file,sheet_name="Validation_Sheet", header=0, engine="openpyxl")
    validate_imp_exp = pd.read_excel(imp_exp_file,sheet_name="Validation_Sheet", header=0, engine="openpyxl")
    #print("Test validation production: ", validate_prod.head())
    #print("Test validation import export: ", validate_imp_exp.head())
    
    balance_dict = {}

    balance_dict["Provinces"] = list(validate_prod.node.unique())
    balance_dict["Commodities"] = list(validate_prod.commodity.unique())

    assertion_list = []

    imports_list = [tuple([p,c,v]) for c in validate_imp_exp.commodity for v in validate_imp_exp.value for p in validate_imp_exp.node if "_imp" in c]
    exports_list = [tuple([p,c,v]) for c in validate_imp_exp.commodity for v in validate_imp_exp.value for p in validate_imp_exp.node if "_exp" in c]
    #for prod_df,ie_df in zip(validate_prod, validate_imp_exp):
    print(exports_list)

    for p,i,e in zip(balance_dict["Provinces"], imports_list, exports_list):
        assertion_list.append(supply_balance(production=list(validate_prod.value),imports=i[2],exports=e[2],demand=pd.read_csv(demand_file, sep=',', header=0)))

    balance_dict["Validation"] = assertion_list

    final_balance = pd.DataFrame.from_dict(balance_dict)
    #print(balance_dict)


def add_new_imp_exp(activity, imp_exp):
    target_year = 2020
    mask = imp_exp[(imp_exp['year_vtg'] >= target_year) & (imp_exp["technology"].str.contains('_exp'))]
    merged_df = pd.merge(activity, mask, left_on=["node_loc", "technology", "year_act"], right_on=["node_loc", "technology", "year_vtg"],
        how="left", suffixes=('', '_imp_exp'))
    merged_df["value"] = np.where(merged_df["value_imp_exp"].notnull(), merged_df["value_imp_exp"], merged_df["value"])
    #activity.update(merged_df)
    #activity.loc[mask, "value"] = merged_df.loc[:,"value_y"].values
    activity = merged_df.drop(columns=["value_imp_exp"])
    print(activity.loc[(activity["node_loc"] == "Alberta") & (activity["technology"] == "oil_exp")])



def h2_processing(input_file_path: str):
    xl = pd.ExcelFile(input_file_path)
    years = list(range(2020, 2051, 5))
    final_table = pd.DataFrame(columns=["share", "node", "year_act", "value"])
    
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        h2_df = df[df["Type"] == "Hydrogen"]
        total_use_df = df[df["Type"] == "Total End-Use"]
        node = sheet.split(' ')[0]
        share = sheet.split(' ')[1]
        if share == "Industrial": 
            share = "share_h2_i"
        elif share == "Transport": 
            share = "share_h2_trp"

        for year in years:
            if str(year) in h2_df.columns:
                value = float(h2_df.loc[:, f"{year}"].values[0] / total_use_df.loc[:,f"{year}"].values[0])
                final_table = final_table._append({"share" : share,
                    "node" : node, "year_act" : year, "value" : value}, ignore_index = True)
    
    rc_values = final_table[final_table["share"].isin(["Residential", "Commercial"])].groupby(["node", "year_act"])["value"].sum().reset_index()
    rc_values["share"] = "share_h2_rc"

    final_table = final_table._append(rc_values, ignore_index = True)

    final_table = final_table[~final_table["share"].isin(["Residential", "Commercial"])]
    
    final_table.to_excel('data\\final_hydrogen_shares.xlsx', index=False)

# Test script

h2_processing("data\\Hydrogen Files For Data Processing.xlsx")
print("File Created!")

'''
#if __name__ == 'main':

test_sheet1 = "data/Production_Data.xlsx"
test_sheet2 = "data/MESSAGE_Imports_Exports.xlsx"
test_sheet3 = "data/historical_activity.csv"
#compare_validate(test_sheet1,test_sheet2, test_sheet3)

DEMANDS_DF = pd.read_csv(test_sheet3, sep=',', header=0)
IMP_EXP_DF = pd.read_excel(test_sheet2, sheet_name="Imports and Exports", header=0)

DEMANDS_DF.to_excel("Historical_Activity_Excel.xlsx", sheet_name="historical_activity")

#add_new_imp_exp(activity=DEMANDS_DF,imp_exp=IMP_EXP_DF)

new_activity = pd.read_excel("data/Adjusted_Historical_Activity_Excel.xlsx", sheet_name="historical_activity")

for t_extr, t_exp in zip(technologies_extr, technologies_exp):
    new_activity = adjust_export_values(new_activity, t_extr, t_exp)

DEMANDS_DF.to_csv("data/adjusted_historical_activity.csv", index=False)
'''