import pandas as pd

def formatdemand(demandfile):
    
    demand = pd.read_excel(demandfile)
    demand.drop(columns = ['Scenario','Model'], inplace = True)
    demand = demand.set_index(["Region","Variable", "Unit"])
    demand = demand.stack().reset_index(level=0).reset_index()
    demand.columns = [ "Variable", "Unit","Year","Region", "Value"]
    demand.sort_values([ "Variable", "Unit","Year","Region", "Value"], inplace=True)
    demand.fillna(0, inplace=True)
    
    return demand