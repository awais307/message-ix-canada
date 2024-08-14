"""
This script implements coal phaseout by 2030 in MESSAGE Canada.
"""

def coal_phase_out(scenario, province):
    """
    Perform a coal phase-out operation on a MESSAGEix scenario.

    This function identifies all technologies related to coal, filters out certain technologies based on specific conditions,
    and then sets the upper bound of activity for these technologies to 0 in the specified years, effectively phasing out these
    coal technologies in the scenario.

    Args:
        scenario (MESSAGEix.Scenario): The scenario to perform the coal phase-out operation on.
        province (str): The province for which the coal phase-out is being implemented.

    Returns:
        None
    """
    # Get all technologies
    technologies = scenario.set('technology')
    
    # Filter technologies containing 'coal'
    coal_technologies = technologies[technologies.str.contains('coal')]
    
    # Further filter technologies
    filtered_coal_technologies = coal_technologies[
        ~coal_technologies.str.contains(r'(air|saline|fresh)$', regex=True, na=False)
    ]
    
    # Filter out technologies starting with 'h2'
    coal_phaseout_tecs = filtered_coal_technologies[
        ~filtered_coal_technologies.str.contains(r'^h2', regex=True)
    ]
    
    # Get the years for the phase-out
    coal_phase_yrs = scenario.set('year')[16:]
    
    # Create a DataFrame for the upper bound of activity
    df = make_df('bound_activity_up',
                 technology=coal_phaseout_tecs,
                 mode='M1',
                 value=0).pipe(
        broadcast,
        node_loc=nodes_tax,
        time='year',
        year_act=coal_phase_yrs,
        unit='-'
    ).pipe(same_node)
    
    df['time'] = 'year'
    
    # Filter out certain rows
    condition = (df['node_loc'] == 'BritishColumbia') & (df['technology'] == 'coal_exp') & (df['year_act'] == 2030)
    filtered_df = df[~condition]
    
    # Update the scenario
    scenario.check_out()
    existing_df = scenario.par('bound_activity_up')
    scenario.remove_par('bound_activity_up', existing_df)
    scenario.add_par('bound_activity_up', filtered_df)
    scenario.commit('Coal phase-out implemented.')

