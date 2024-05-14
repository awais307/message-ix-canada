import pandas as pd
import numpy as np



def demand_supply_balance(production, demand, mode='exports'):
    imports = demand - production
    exports = demand - 2 * imports

    match mode:
        case 'exports':
            return exports
        case 'imports':
            return imports
        case _:
            raise Exception("Mode not recognized. Neither 'imports', nor 'exports'")

def downscale(parameter, scaler):
    return parameter * scaler


def input_deducer(input_file):

    with pd.ExcelFile(input_file) as xl_file:
        xl_sheets = xl_file.sheet_names
        for i in xl_sheets:
            df = pd.read_excel(xl_file, sheet_name=i, index_col=0, header=0)
            df.fillna(0) # Fill in with 0 for missing values
            df.apply()

