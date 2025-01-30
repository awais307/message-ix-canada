"""
This module provides functions to implement various energy policies in MESSAGEix scenarios, 
including hydrogen shares, federal carbon tax, coal phase-out, investment tax credits, and provincial carbon tax.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def add_federal_carbon_tax(scenario, province):
    """
    Add a provincial carbon tax to a MESSAGEix scenario.

    This function modifies the provided MESSAGEix scenario to include a provincial carbon tax 
    for a specified province. The specific implementation details, such as the tax rates, 
    affected sectors, and the time period for the tax, should be added within this function.

    Args:
        scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the provincial carbon tax will be added.
        province (str): The name of the province for which the carbon tax is being implemented.

    Returns:
        None
    """
    #TODO: At the moment, it reads in a file with a fixed tax for each province. we need to
    # mod this to be dynamic for different prices. 

    # Read in the carbon tax rates for each province
    #TODO Fix the path
    df = pd.read_csv(Path('data')/'carbon_tax_rates.csv')
    # Fix the scenario 
    scenario.add_par('tax_emission', df)
    
    scenario.commit('Add carbon tax to the scenario')
    pass
