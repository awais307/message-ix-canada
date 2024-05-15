import pandas as pd
import numpy as np



def demand_supply_balance(production, demand):
    imports = demand - production
    exports = demand - 2 * imports
    return tuple(imports, exports)

def downscale(parameter, scaler):
    return parameter * scaler


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
            df.apply()

