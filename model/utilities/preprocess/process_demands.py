import pandas as pd
import numpy as np
from pathlib import Path

import pandas as pd
import numpy as np
from itertools import product
from scipy.optimize import linprog
import warnings
warnings.filterwarnings('ignore')
script_dir = Path(__file__).parent
from model.utilities.preprocess.process_gdp_population import process_gdp_population_data

def adjust_demands(scenario):
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
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir / '../../../data'
    # File names of GDP and population data. If these will be changed often, consider adding parameter for the name of the population and GDP data file.
    gdp_data = data_dir / 'gdp/gdp_messageca_prov.csv'
    population_data = data_dir / 'population/pop_messageca_prov.csv'
    
    ssp_df = process_gdp_population_data(gdp_data,population_data)
    demand = scenario.par('demand')
    df_ca = demand.groupby(['year', 'commodity', 'level', 'time', 'unit']).sum().reset_index()
    df_ca['node'] = 'Canada'

    pc = df_ca.groupby('commodity').apply(
        lambda x: x.sort_values('year').assign(pct_change=lambda y: y['value'].pct_change().fillna(0))
    )

    # Reset index to flatten the dataframe
    pc = pc.reset_index(drop=True)

    # Keep only the relevant columns: 'year', 'commodity', and 'pct_change'
    pc = pc[['year', 'commodity', 'pct_change']]
    hist_act_df = scenario.par('historical_activity')
    dmds_dict = {}
    historical_years = hist_act_df['year_act'].unique().tolist()
    #historical_years
    demand_years = demand['year'].unique().tolist()
    cmdtys = demand['commodity'].unique().tolist()

    historical_demand = []
    for cmdty in cmdtys:
        for province in ssp_df['iso'].unique():
            for year in demand_years: 
                if year in historical_years:
                    # Append the DataFrame to the list
                    historical_demand.append(demand[(demand['year'] == year) & (demand['commodity'] == cmdty) & (demand['node'] == province)])

    # Concatenate all DataFrames in the list to create a single DataFrame
    historical_demand_df = pd.concat(historical_demand, ignore_index=True)
    #historical_demand_df.value

    ha = historical_demand_df
    dmds = []
    for cmdty in cmdtys:
        for province in ssp_df['iso'].unique():
            for year in demand_years: 
                if year in historical_years:
                    # Append the DataFrame to the list
                    dm = ha.loc[(ha['year'] == year) & (ha['node']==province)&(ha['commodity']==cmdty)]
                    dm = dm[['node','value']]

                    gdp = []
                    gdpc = []
                    gdp.append(ssp_df.gdp.to_numpy()[0])
                    gdpc.append(ssp_df.gdpc.to_numpy()[0])

                    dm = pd.DataFrame({'node':dm.node.to_numpy(),
                                    'commodity':cmdty,
                                    'level':'useful',
                                    'year':year,
                                    'time':'year',

                                        'value':dm.value.to_numpy(),
                                        'unit':'GWa',
                                        'ei':dm.value.to_numpy()/gdp,
                                        'gdp':gdp,
                                        'gdpc':gdpc,'year':year})
                    dmds.append(dm)

                    dt = dm.value
                    dm0 = dm
                #else we are in the demand years
                else:
                    pct_change = pc.loc[(pc['year'] == year)&(pc['commodity']==cmdty),'pct_change'].values[0]
                    dt = dm.value*(1+pct_change)
                    
                    dm0 = dm
                    gdpf = []
                    gdpcf = []

                    inds = (ssp_df['year']==year)
                    gdpf.append(ssp_df.loc[inds,'gdp'].to_numpy()[0])
                    gdpcf.append(ssp_df.loc[inds,'gdpc'].to_numpy()[0])

                    # unload some variables and call LP downscaling algorithm
                    names = dm0.node.to_numpy()
                    vl = dm0.value.to_numpy()
                    gdpco = dm0.gdpc.to_numpy()

                    # don't allow 0 intensities in future time steps if not biomass technologies
                    if not 'biomass' in cmdty:
                        ei = vl / gdpco
                    # ei[np.where(ei==0)] = min(ei[ei.nonzero()])
                        vl = ei * gdpco
                    print(dt,vl,gdpco,gdpcf,gdpf,names)

                    # the above simplifying parameters defined as:
                    beta = gdpco * vl / gdpco
                    phi = gdpcf / gdpco - 1

                    # x = [alpha, delta_1, delta_2, ...., delta_n]    
                    # LP objective function coefficients for minimizing maximum difference in growth rates
                    cobj = [1]
                    cobj.extend([0]*len(names))
                    cobj = np.array(cobj)

                    # maxmin abs value constraint upper bound 1
                    a = np.array([-1]*len(names))
                    a.shape=(len(names),1)
                    b = np.identity(len(names))
                    Aub1 = np.concatenate((a,b),axis=1)
                    bub1 = phi
                    bub1.shape = (len(names),1)

                    # maxmin abs value constraint upper bound 2
                    a = np.array([-1]*len(names))
                    a.shape=(len(names),1)
                    b = np.identity(len(names))
                    b *= -1
                    Aub2 = np.concatenate((a,b),axis=1)
                    bub2 = -1*phi
                    bub2.shape = (len(names),1)

                    # non negativity for absolute value
                    Aub3 = np.array([-1])
                    Aub3 = np.append(Aub3,[0]*len(names))
                    Aub3.shape = (1,(len(names)+1))
                    bub3 = np.array([[0]])
                    Aub = np.concatenate((Aub1,Aub2,Aub3),axis=0)
                    bub = np.concatenate((bub1,bub2,bub3),axis=0)

                    # Equality constraint for ensuring the country balances match the regional target
                    Aeq = np.array(np.append([0],beta))
                    Aeq.shape = (1,(1+len(names)))
                    beq = np.array([[dt-sum(beta)]])
                    beq.shape = (1,1)

                    # Call LP solver
                    res = linprog(
                    c = cobj,
                    A_ub=Aub,
                    b_ub=bub,
                    A_eq=Aeq,
                    b_eq=beq,
                    bounds=(-np.inf, np.inf),
                    options={"disp":False,"tol":3.6e-10})

                    # Return data frame with updated parameters
                    val = []
                    for i in range(1,(len(names)+1)):
                        val.append(gdpcf[i-1]*(vl[i-1]/gdpco[i-1])*(1+res.x[i]))

                    dmf = pd.DataFrame({'node':names,'value':val})
                    
                    #print(dmf.value)
                    #print(dt)
                    # update demand state variables
                    dm = pd.DataFrame({'node':dmf.node.to_numpy(),
                                    'commodity':cmdty,
                                    'level':'useful',
                                    'year':year,
                                    'time':'year',
                                        'value':dmf.value.to_numpy(),
                                        'unit':'GWa',
                                        'ei':dmf.value.to_numpy()/gdpf,
                                        'gdp':gdpf,
                                        'gdpc':gdpcf,'commodity':cmdty,'year':year})
                    
                    
                    dmds.append(dm)

    dmds = pd.concat(dmds, ignore_index=True)
    dmds.drop(columns=['ei','gdp','gdpc'],inplace=True)
    scenario.check_out() 
    df = scenario.par('demand')
    scenario.remove_par('demand',df)
    scenario.add_par('demand', dmds)
    
    scenario.commit('Updated demands')