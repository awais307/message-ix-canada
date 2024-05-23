import pandas as pd
import numpy as np
import os


def supply_balance(production, imports, exports):
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
'''
def input_deducer(input_file):

    with pd.ExcelFile(input_file) as xl_file:
        xl_sheets = xl_file.sheet_names
        for i in xl_sheets:
            df = pd.read_excel(xl_file, sheet_name=i, index_col=0, header=0)
            calculation_df = df.loc['Export':'Total Production',:]
            demand = df.loc['Demand',:]
            production = df.loc['Total Production',:]
            calculation = demand_supply_balance(production, demand)
            imports = calculation[0]
            exports = calculation[1]
            df[df["Export"]] = exports
            df[df["Import"]] = imports
            write_excel(filename=input_file, sheetname=i, dataframe=df)
'''
def compare_validate(production_file, imp_exp_file):
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
    #print(imports_list[0][0])

    for p,i,e in zip(balance_dict["Provinces"], imports_list, exports_list):
        assertion_list.append(supply_balance(production=list(validate_prod.value),imports=i[2],exports=e[2]))

    balance_dict["Validation"] = assertion_list

    final_balance = pd.DataFrame.from_dict(balance_dict)
    print(balance_dict)



    

# Test script
#if __name__ == 'main':
test_sheet1 = "data/MESSAGE_Imports_Exports.xlsx"
test_sheet2 = "data/Production_Data.xlsx"
compare_validate(test_sheet2,test_sheet1)