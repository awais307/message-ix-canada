import pandas as pd
import numpy as np
from pathlib import Path

def update_historical_activity(scenario, path):
    """
    Update the historical activity parameter in the scenario with data from a specified path.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        path (str or Path): Path to the the historical activity data.
    """
    scenario.check_out() 
    df = scenario.par('historical_activity')
    df_new = pd.read_csv(path)
    scenario.remove_par('historical_activity', df)
    scenario.add_par('historical_activity', df_new)
    scenario.commit('Updated historical activity based on new data')

def process_population_data(path):
    """
    Process population data for the model.
    
    Args:
        data_path (str or Path): Path to the CSV file containing raw population data.
    
    Returns:
        pd.DataFrame: DataFrame containing processed population data.
    """
    data = pd.read_csv(path)
    data.rename(columns={'Unnamed: 0': 'Year'}, inplace=True)
    data['Year'] = pd.to_datetime(data['Year'], format='%Y')
    pivoted_data = data.melt(id_vars=['Year'], var_name='Province', value_name='Population')
    pivoted_data.set_index('Year', inplace=True)
    pivoted_data.sort_index(inplace=True)
    pivoted_data['Population'] = pivoted_data['Population'].ffill().bfill()
    resampled_data = pivoted_data.groupby('Province').resample('5A').mean().interpolate(method='linear')
    resampled_data = resampled_data.reset_index()
    resampled_data['Year'] = resampled_data['Year'].dt.year - 1
    resampled_data['Province'] = resampled_data['Province'].str.replace(' ', '')
    return resampled_data

def process_gdp_data(dpath):
    """
    Process GDP data for the model.
    
    Args:
        data_path (str or Path): Path to the CSV file containing raw GDP data.
    
    Returns:
        pd.DataFrame: DataFrame containing processed GDP data.
    """
    df_gdp = pd.read_csv(path)
    gdp_data = df_gdp.melt(id_vars=['prov'], var_name='Year', value_name='GDP')
    gdp_data.rename(columns={'prov': 'Province'}, inplace=True)
    gdp_data['Province'] = gdp_data['Province'].str.replace(' ', '')
    return gdp_data

def add_population_gdp_to_scenario(scenario, population_data, gdp_data):
    """
    Add processed population and GDP data to the scenario.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        population_data (pd.DataFrame): DataFrame containing processed population data.
        gdp_data (pd.DataFrame): DataFrame containing processed GDP data.
    """
    population_data.rename(columns={'Population': 'value', 'Province': 'node_loc', 'Year': 'year_act'}, inplace=True)
    population_data['technology'] = 'Population'
    population_data['mode'] = 'P'
    population_data['time'] = 'year'
    population_data['unit'] = 'GWa/a'

    gdp_data.rename(columns={'GDP': 'value', 'Province': 'node_loc', 'Year': 'year_act'}, inplace=True)
    gdp_data['technology'] = 'GDP'
    gdp_data['mode'] = 'P'
    gdp_data['time'] = 'year'
    gdp_data['unit'] = 'GWa/a'

    concatenated_df_socio = pd.concat([population_data, gdp_data])

    df = scenario.par('bound_activity_lo')
    df_filtered = df[~df['technology'].isin(['Population', 'GDP'])]
    df_bound_new = pd.concat([df_filtered, concatenated_df_socio])

    scenario.check_out()
    scenario.add_par('bound_activity_lo', df_bound_new)
    scenario.commit('Added population and GDP bounds')

def adjust_demands(scenario, population_data, gdp_data, hist_act_df, ssp_df, demand_yrs):
    """
    Adjust demands in the scenario based on population and GDP data.
    
    Args:
        scenario (ixmp.Scenario): The MESSAGEix scenario to update.
        population_data (pd.DataFrame): DataFrame containing processed population data.
        gdp_data (pd.DataFrame): DataFrame containing processed GDP data.
        hist_act_df (pd.DataFrame): DataFrame containing historical activity data.
        ssp_df (pd.DataFrame): DataFrame containing SSP population and GDP data.
        demand_yrs (list): List of years for which demands are to be adjusted.
    
    Returns:
        pd.DataFrame: DataFrame containing updated demand data.
    """
    df_demand = scenario.par('demand')
    df_region = df_demand.groupby(['year', 'commodity', 'level', 'time', 'unit']).sum().reset_index()
    df_region['node'] = 'Canada'
    cmdtys = df_region['commodity'].unique().tolist()

    dmds_dict = {}

    for cmdty in cmdtys:
        for province in ssp_df['iso'].unique():
            province_df = ssp_df[ssp_df['iso'] == province]
            dff = df_region[df_region['commodity'] == cmdty].sort_values('year').reset_index(drop=True)
            dff['node'] = province
            dff['pc'] = dff['value'].pct_change(periods=1)
            dff = dff.replace([np.inf, -np.inf, np.nan], 0)

            tec_list = list(set((scenario.par('output', {'level': dff.level.values[0], 'commodity': cmdty}))['technology']))
            if len(tec_list) > 1:
                ha = hist_act_df.loc[hist_act_df.technology.isin(tec_list)]
            else:
                ha = hist_act_df.loc[hist_act_df['technology'] == tec_list[0]]

            ha['value'] = pd.to_numeric(ha['value'], errors='coerce')
            ha = ha[ha['node_loc'].str.strip().replace(" ", "") == province.strip().replace(" ", "")]

            initial_demand = ha.loc[ha['year_act'] == demand_yrs[0]].groupby('node_loc')['value'].sum().reset_index()
            initial_demand_value = initial_demand['value'].sum() if not initial_demand.empty else 0
            dff.loc[dff['year'] == demand_yrs[1], 'value'] = initial_demand_value

            for ind in range(1, len(dff)):
                dff.loc[ind, 'value'] = dff.loc[ind - 1, 'value'] * (1 + dff.loc[ind, 'pc'])

            if cmdty not in dmds_dict:
                dmds_dict[cmdty] = []
            dmds_dict[cmdty].append(dff.copy())

    demand_df = pd.concat([pd.concat(dmds_dict[cmdty], ignore_index=True) for cmdty in dmds_dict], ignore_index=True)
    scenario.add_par('demand', demand_df)

    return demand_df

def downscale_demands(target, initial, income_i, income_f, gdp_f, names):
    """
    Downscale demands to match regional targets.
    
    Args:
        target (float): Target demand value.
        initial (np.array): Initial demand values.
        income_i (np.array): Initial income values.
        income_f (np.array): Final income values.
        gdp_f (np.array): Final GDP values.
        names (list): List of region names.
    
    Returns:
        pd.DataFrame: DataFrame containing downscaled demand values.
    """
    beta = income_f * initial / income_i
    phi = income_f / income_i - 1
    
    cobj = [1]
    cobj.extend([0]*len(names))
    cobj = np.array(cobj)

    a = np.array([-1]*len(names))
    a.shape=(len(names),1)
    b = np.identity(len(names))
    Aub1 = np.concatenate((a,b),axis=1)
    bub1 = phi
    bub1.shape = (len(names),1)
    
    a = np.array([-1]*len(names))
    a.shape=(len(names),1)
    b = np.identity(len(names))
    b *= -1
    Aub2 = np.concatenate((a,b),axis=1)
    bub2 = -1*phi
    bub2.shape = (len(names),1)
    
    Aub3 = np.array([-1])
    Aub3 = np.append(Aub3,[0]*len(names))
    Aub3.shape = (1,(len(names)+1))
    bub3 = np.array([[0]])
    Aub = np.concatenate((Aub1,Aub2,Aub3),axis=0)
    bub = np.concatenate((bub1,bub2,bub3),axis=0)

    Aeq = np.array(np.append([0],beta))
    Aeq.shape = (1,(1+len(names)))
    beq = np.array([[target-sum(beta)]])
    beq.shape = (1,1)

    res = linprog(
        c=cobj,
        A_ub=Aub,
        b_ub=bub,
        A_eq=Aeq,
        b_eq=beq,
        bounds=(-np.inf, np.inf),
        options={"disp": True, "tol": 3.6e-10}
    )

    val = []
    for i in range(1, (len(names) + 1)):
        val.append(income_f[i - 1] * (initial[i - 1] / income_i[i - 1]) * (1 + res.x[i]))

    df = pd.DataFrame({'node': names, 'value': val})
    return df
