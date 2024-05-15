import pandas as pd
import numpy as np
import os


def demand_supply_balance(production, demand):
    imports = demand - production
    exports = demand - 2 * imports
    return tuple(imports, exports)

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

# Test script
if __name__ == 'main':
    test_sheet = "../Input_2021.xlsx"
    input_deducer(test_sheet)