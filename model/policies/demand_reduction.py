"""
This module provides functions to implement climate policies in MESSAGEix scenarios, 
including federal carbon tax and coal phase-out.
"""

from pathlib import Path
import yaml

def demand_reduction(scenario):
    """
    Reduces demand for a MESSAGEix scenario.

    This function will modify the provided MESSAGEix scenario to include a federal carbon tax. 
    The specific implementation details, such as the tax rates and the affected sectors, 
    should be added within this function.

    Args:
        scenario (MESSAGEix.Scenario): The MESSAGEix scenario to which the federal carbon tax will be added.

    Returns:
        None
    """

    data = scenario.par('demand')
    # Loop through each unique combination of node and commodity
    nodes = data['node'].unique()
    commodities = data['commodity'].unique()

    # Define the reduction factors for the key years
    # reduction_factors = {
    #     2020: 1.0,    # No reduction in 2020
    #     2030: 0.94,   # 6% reduction by 2030
    #     2040: 0.87,    # 13% reduction by 2040
    #     2050: 0.78,   # 18% reduction by 2050
    #     2060: 0.8    # 20% reduction by 2060
    # }
    policies_config_path = Path("model/policies/policies_input.yaml")
    with open(policies_config_path, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
        reduction_factors = data['reduction_factors']
        
    # Print the values as a dictionary
    print(data)

    # Create a function to calculate the reduction factor for any given year
    def calculate_reduction_factor(year):
        if year in reduction_factors:
            return reduction_factors[year]
        else:
            # Linear interpolation
            if year < 2050:
                return 1.0 + (0.82 - 1.0) * (year - 2020) / (2050 - 2020)
            else:
                return 0.82 + (0.80 - 0.82) * (year - 2050) / (2060 - 2050)

    # Function to apply reduction
    def apply_reduction(group):
        for index, row in group.iterrows():
            year = row['year']
            reduction_factor = calculate_reduction_factor(year)
            group.at[index, 'value'] = row['value'] * reduction_factor
        return group

    # Apply the reduction to each combination of node and commodity
    for node in nodes:
        for commodity in commodities:
            mask = (data['node'] == node) & (data['commodity'] == commodity)
            data.loc[mask] = apply_reduction(data.loc[mask])



    # Display the first few rows of the modified data
    data.head(10)
    pass