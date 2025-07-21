from collections import defaultdict
import os

import message_ix
import pandas as pd
from message_ix import make_df, Scenario

from message_ix_models import ScenarioInfo
from message_ix_models.model.material.data_util import (
    calculate_ini_new_cap,
    read_sector_data,
    read_timeseries,
)
from message_ix_models.model.material.material_demand import material_demand_calc
from message_ix_models.model.material.util import get_ssp_from_context, read_config
from message_ix_models.util import (
    broadcast,
    nodes_ex_world,
    package_data_path,
    same_node,
)

##################################################################################
import logging
from message_ix_models.model.material.data_util import (
    add_ccs_technologies,
    add_cement_bounds_2020,
    add_coal_lowerbound_2020,
    add_elec_i_ini_act,
    add_elec_lowerbound_2020,
    add_emission_accounting,
    add_new_ind_hist_act,
    modify_baseyear_bounds,
    modify_demand_and_hist_activity,
    modify_industry_demand,
)
from message_ix_models.model.material.util import read_config
from message_ix_models.util.compat.message_data import (
    calibrate_UE_gr_to_demand,
    calibrate_UE_share_constraints,
)
from message_ix_models.util.compat.message_data import (
    manual_updates_ENGAGE_SSP2_v417_to_v418 as engage_updates,
)
from message_ix_models.util.scenarioinfo import ScenarioInfo
from message_ix_models.model.build import apply_spec

from typing import Callable, Dict, List, Mapping, Optional, Union

import ixmp
from sdmx.model.v21 import Code

from message_ix_models.util import add_par_data, strip_par_data, identify_nodes, package_data_path
from message_ix_models.util.ixmp import maybe_check_out, maybe_commit
from message_ix_models.util.scenarioinfo import ScenarioInfo, Spec
##################################################################################

log = logging.getLogger(__name__)

def ellipsize(elements: List) -> str:
    """Generate a short string representation of `elements`.

    If the list has more than 5 elements, only the first two and last two are shown,
    with "..." between.
    """
    if len(elements) > 5:
        return ", ".join(map(str, elements[:2] + ["..."] + elements[-2:]))
    else:
        return ", ".join(map(str, elements))

def _add_unit(mp: ixmp.Platform, unit: str, comment: str) -> None:
    """Handle exceptions in :meth:`.Platform.add_unit`."""
    # TODO move upstream to ixmp.JDBCBackend
    log.info(f"Add unit {repr(unit)}")
    try:
        mp.add_unit(unit, comment)
    except Exception as e:  # pragma: no cover
        if "Error assigning an unit-key-id mapping" in str(e) and "" == str(unit):
            log.warning(f"…skip {repr(unit)} (ixmp.JDBCBackend with Oracle database)")
        else:
            raise

# FIXME Reduce complexity from 14 to ≤13
def apply_spec(  # noqa: C901
    scenario: Scenario,
    spec: Union[Spec, Mapping[str, ScenarioInfo]],
    data: Optional[Callable] = None,
    **options,
):
    """Apply `spec` to `scenario`.

    Parameters
    ----------
    spec : .Spec
        Specification of changes to make to `scenario`.
    data : callable, optional
        Function to add data to `scenario`. `data` can either manipulate the scenario
        directly, or return a :class:`dict` compatible with :func:`.add_par_data`.

    Other parameters
    ----------------
    dry_run : bool
        Don't modify `scenario`; only show what would be done. Default :obj:`False`.
        Exceptions will still be raised if the elements from ``spec['required']`` are
        missing; this serves as a check that the scenario has the required features for
        applying the spec.
    fast : bool
        Do not remove existing parameter data; increases speed on large scenarios.
    quiet : bool
        Only show log messages at level ``ERROR`` and higher. If :obj:`False` (default),
        show log messages at level ``DEBUG`` and higher.
    message : str
        Commit message.

    See also
    --------
    .add_par_data
    .strip_par_data
    .Code
    .ScenarioInfo
    """
    dry_run = options.get("dry_run", False)
    fast = options.get("fast", False)

    log.setLevel(logging.ERROR if options.get("quiet", False) else logging.DEBUG)

    if not dry_run:
        try:
            scenario.remove_solution()
        except ValueError:
            pass
        maybe_check_out(scenario)

    dump: Dict[str, pd.DataFrame] = {}  # Removed data

    # Sort the list of sets by the number of dimensions; this places basic (non-indexed)
    # sets first. Elements for these sets must be added before elements for indexed
    # sets that may reference them.
    sets = sorted((len(scenario.idx_sets(s)), s) for s in scenario.set_list())

    # Existing 'region' codes stored on the Platform associated with `scenario`
    platform_regions = set(scenario.platform.regions()["region"])

    for _, set_name in sets:
        # Check whether this set is mentioned at all in the spec
        if 0 == sum(map(lambda info: len(info.set[set_name]), spec.values())):
            # Not mentioned; don't do anything
            continue

        log.info(f"Set {repr(set_name)}")

        # Base contents of the set
        base_set = scenario.set(set_name)
        # Unpack a multi-dimensional/indexed set to a list of tuples
        base = (
            list(base_set.itertuples(index=False))
            if isinstance(base_set, pd.DataFrame)
            else base_set.tolist()
        )

        log.info(f"  {len(base)} elements")
        # log.debug(', '.join(map(repr, base)))  # All elements; verbose

        # Check for required elements
        require = spec["require"].set[set_name]
        log.info(f"  Check {len(require)} required elements")

        # Raise an exception about the first missing element
        missing = list(filter(lambda e: e not in base, require))
        if missing:
            print(f"  {len(missing)} elements not found: {missing!r}")
            log.error(f"  {len(missing)} elements not found: {missing!r}")
            #raise ValueError

        # Remove elements and associated parameter values
        for element in spec["remove"].set[set_name]:
            strip_par_data(
                scenario,
                set_name,
                element,
                dry_run=dry_run,
                dump=None if fast else dump,
            )

        # Add elements
        add = [] if dry_run else spec["add"].set[set_name]
        for element in add:
            name = element.id if isinstance(element, Code) else element
            scenario.add_set(set_name, name)
            if set_name == "node" and name not in platform_regions:
                scenario.platform.add_region(name, "region")

        if len(add):
            log.info(f"  Add {len(add)} element(s)")
            log.debug("  " + ellipsize(add))

        log.info("  ---")

    if not fast:
        N_removed = sum(len(d) for d in dump.values())
        log.info(f"{N_removed} total rows removed")

    # Add units to the Platform before adding data
    for unit in spec["add"].set["unit"]:
        unit = unit if isinstance(unit, Code) else Code(id=unit, name=unit)
        _add_unit(scenario.platform, unit.id, str(unit.name))

    # Add data
    if callable(data):
        result = data(scenario, dry_run=dry_run)
        if result:
            # `data` function returned some data; use add_par_data()
            add_par_data(scenario, result, dry_run=dry_run)

    # Finalize
    log.info("Commit results.")
    maybe_commit(
        scenario,
        condition=not dry_run,
        message=options.get("message", f"{__name__}.apply_spec()"),
    )

def gen_mock_demand_cement(scenario: message_ix.Scenario) -> pd.DataFrame:
    s_info = ScenarioInfo(scenario)
    nodes = s_info.N
    nodes.remove("World")

    # 2019 production by country (USGS)
    # p43 of https://pubs.usgs.gov/periodicals/mcs2020/mcs2020-cement.pdf

    # For R12: China and CPA demand divided by 0.1 and 0.9.

    # The order:
    # r = ['R12_AFR', 'R12_RCPA', 'R12_EEU', 'R12_FSU', 'R12_LAM', 'R12_MEA',\
    # 'R12_NAM', 'R12_PAO', 'R12_PAS', 'R12_SAS', 'R12_WEU',"R12_CHN"]
    nodes.append('R12_NAM')
    if "R12_NAM" in nodes:
        #nodes.remove("R12_GLB")
        nodes.remove('R12_NAM')
        sheet_n = "data_R12"
        region_set = "R12_"
        # [
        #     {"Province": "Ontario", "Estimated Cement Demand (Mt)": 5.195},
        #     {"Province": "Quebec", "Estimated Cement Demand (Mt)": 2.964},
        #     {"Province": "British Columbia", "Estimated Cement Demand (Mt)": 1.832},
        #     {"Province": "Alberta", "Estimated Cement Demand (Mt)": 1.565},
        #     {"Province": "Manitoba", "Estimated Cement Demand (Mt)": 0.466},
        #     {"Province": "Saskatchewan", "Estimated Cement Demand (Mt)": 0.4},
        #     {"Province": "Nova Scotia", "Estimated Cement Demand (Mt)": 0.333},
        #     {"Province": "New Brunswick", "Estimated Cement Demand (Mt)": 0.266},
        #     {"Province": "Newfoundland and Labrador", "Estimated Cement Demand (Mt)": 0.167},
        #     {"Province": "Prince Edward Island", "Estimated Cement Demand (Mt)": 0.057},
        #     {"Province": "Northwest Territories", "Estimated Cement Demand (Mt)": 0.015},
        #     {"Province": "Yukon", "Estimated Cement Demand (Mt)": 0.014},
        #     {"Province": "Nunavut", "Estimated Cement Demand (Mt)": 0.013}
        # ]
        #['Canada', 'Alberta', 'BritishColumbia', 'Manitoba', 'NewBrunswick', 'NewfoundlandandLabrador', 'NorthwestTerritories', 'NovaScotia', 'Nunavut', 'Ontario', 'PrinceEdwardIsland', 'Quebec', 'Saskatchewan', 'Yukon']
        demand2020_top = [13.287, 1.565, 1.832, 0.466, 0.266, 0.167, 0.015, 0.333, 0.013, 5.195, 0.057, 2.964, 0.4, 0.014]
        historical_activity = {
            'BC': 3,
            'AB': 2.2,
            'ON': 6.8,
            'QC': 2.3,
            'MN': 0.4,
            'SK': 0.3,
            'NS':  0.25,
            'NB': 0.23,
            'NL': 0.15,
            'PEI': 0.05,
            'NorthwestTerritories': 0.01,
            'Nunavut':0.01,
            'Yukon':0.01         
        }

        # # Build path in an OS-independent way
        # file_path = os.path.join("data", "msg_materials_cement", "CEEDC estimates of energy use_provincial.xlsx")

        # cement_demand_df = pd.read_csv(csv_path)
        
        # Build path in an OS-independent way
        csv_path = os.path.join("data", "msg_materials_cement", "CEEDC estimates of energy use_provincial(Original).csv")
        cement_demand_df = pd.read_csv(csv_path)

        cement_demand_df = cement_demand_df[cement_demand_df['commodity']=='Cement']
        cement_demand_df = cement_demand_df[cement_demand_df['GJ']=='Total energy']
        cement_demand_df['province'] = (
            cement_demand_df['province']
            .astype(str)
            .str.replace(' ', '')
        )
        cement_demand_df = cement_demand_df[cement_demand_df['province'].isin(nodes)]


        cement_demand_df['2020'] = (
            cement_demand_df['2020']
            .astype(str)
            .str.replace(',', '')
            .str.replace('$', '')
            .astype(float) / (4.2 * 10**6)
        ) # conversion from GJ to Mt

        cement_demand_dict = dict(zip(cement_demand_df['province'] ,cement_demand_df['2020']))
        # the rest (~900 Mt) allocated by % values in http://www.cembureau.eu/media/clkdda45/activity-report-2019.pdf
        # demand2020_rest = [
        #     4100 * 0.051 - 76,
        #     (4100 * 0.14 - 155) * 0.2 * 0.1,
        #     4100 * 0.064 * 0.5,
        #     4100 * 0.026 - 57,
        #     4100 * 0.046 * 0.5 - 55,
        #     (4100 * 0.14 - 155) * 0.2,
        #     4100 * 0.046 * 0.5,
        #     12,
        #     4100 * 0.003,
        #     (4100 * 0.14 - 155) * 0.6,
        #     4100 * 0.064 * 0.5 - 51,
        #     (4100 * 0.14 - 155) * 0.2 * 0.9,
        # ]
    else:
        nodes.remove("R11_GLB")
        sheet_n = "data_R11"
        region_set = "R11_"

        demand2020_top = [76, 2295, 0, 57, 55, 60, 89, 54, 129, 320, 51]
        # the rest (~900 Mt) allocated by % values in http://www.cembureau.eu/media/clkdda45/activity-report-2019.pdf
        # demand2020_rest = [
        #     4100 * 0.051 - 76,
        #     (4100 * 0.14 - 155) * 0.2,
        #     4100 * 0.064 * 0.5,
        #     4100 * 0.026 - 57,
        #     4100 * 0.046 * 0.5 - 55,
        #     (4100 * 0.14 - 155) * 0.2,
        #     4100 * 0.046 * 0.5,
        #     12,
        #     4100 * 0.003,
        #     (4100 * 0.14 - 155) * 0.6,
        #     4100 * 0.064 * 0.5 - 51,
        # ]

    prov_pop_dict = pd.read_csv('data/population/pop_messageca_prov.csv')
    years = [int(v) for v in list(prov_pop_dict['Year'].unique())]
    provs = list(prov_pop_dict['Province'].unique())
    prov_pop_dict = {f'{a.replace(' ','')}.{b}': c*(10**3) for a, b, c in zip(prov_pop_dict['Province'], prov_pop_dict['Year'], prov_pop_dict['Population'])}
    
    for year in years:
        prov_pop_dict[f'Canada.{year}'] = sum([prov_pop_dict[f'{prov.replace(' ','')}.{year}'] for prov in provs])
    
    gdp_df = pd.read_csv('./data/gdp/openinsights_GDP_2010USD.csv')
    gdp_df = gdp_df[gdp_df['year'] > 2015]

    # Group by variable, year, SSP and sum the values
    canada_totals = gdp_df.groupby(['variable', 'year', 'SSP'], as_index=False)['value'].sum()

    # Add a new 'region' column set to 'Canada'
    canada_totals['region'] = 'Canada'

    # Retain consistent 'unit'
    canada_totals['unit'] = 'billion 2010USD/yr'

    # Reorder columns to match gdp_df
    canada_totals = canada_totals[gdp_df.columns]

    # Append to original dataframe
    gdp_df = pd.concat([gdp_df, canada_totals], ignore_index=True)
    
    gdp_per_capita_dict = {f'{a.replace(' ','')}.{b}': c*(10**9)/prov_pop_dict[f'{a.replace(' ','')}.{b}'] for a, b, c in zip(gdp_df['region'], gdp_df['year'], gdp_df['value'])}


    # # SSP2 R11 baseline GDP projection
    # gdp_growth = pd.read_excel(
    #     package_data_path("material", "iamc_db ENGAGE baseline GDP PPP.xlsx"),
    #     sheet_name=sheet_n,
    # )

    # gdp_growth = gdp_growth.loc[
    #     (gdp_growth["Scenario"] == "baseline") & (gdp_growth["Region"] != "World")
    # ].drop(["Model", "Variable", "Unit", "Notes", 2000, 2005], axis=1)

    d = [a for a in demand2020_top]
    # gdp_growth["Region"] = region_set + gdp_growth["Region"]

    # # Regions setting for IMAGE
    # region_cement = pd.read_excel(
    #     package_data_path("material",  "CEMENT.BvR2010.xlsx"),
    #     sheet_name="Timer_Regions", skiprows=range(0,3))[['Region #', 'Name']]\
    #     .drop_duplicates().sort_values(by='Region #')
    #
    # region_cement = region_cement.loc[region_cement['Region #'] < 999]
    # region_cement['node'] = \
    #     ['R11_NAM', 'R11_NAM',
    #      'R11_LAM', 'R11_LAM',
    #      'R11_LAM', 'R11_LAM',
    #      'R11_AFR', 'R11_AFR',
    #      'R11_AFR', 'R11_AFR',
    #      'R11_WEU', 'R11_EEU',
    #      'R11_EEU', 'R11_FSU',
    #      'R11_FSU', 'R11_FSU',
    #      'R11_MEA', 'R11_SAS',
    #      'R11_PAS', 'R11_CPA',
    #      'R11_PAS', 'R11_PAS',
    #      'R11_PAO', 'R11_PAO',
    #      'R11_SAS', 'R11_AFR']
    #
    # # Cement demand 2010 [Mt/year] (IMAGE)
    # demand2010_cement = pd.read_excel(
    #     package_data_path("material",  "CEMENT.BvR2010.xlsx"),
    #     sheet_name="Domestic Consumption", skiprows=range(0,3)).\
    #     groupby(by=["Region #"]).sum()[[2010]].\
    #     join(region_cement.set_index('Region #'), on='Region #').\
    #     rename(columns={2010:'value'})
    #
    # demand2010_cement = demand2010_cement.groupby(by=['node']).sum().reset_index()
    # demand2010_cement['value'] = demand2010_cement['value'] / 1e9 # kg to Mt

    # Directly assigned countries from the table on p43
    demand2020_cement = (
        pd.DataFrame({"Region": cement_demand_df['province'] , "value": cement_demand_df['2020']})
        #.join(gdp_growth.set_index("Region"), on="Region")
        .rename(columns={"Region": "node"})
    )
    new_demand2020_cement = []
    for row in demand2020_cement.iterrows():
        new_row = [row[1]['node'], row[1]['value']]
        for year in years:
            new_row.append(gdp_per_capita_dict[f'{row[1]['node']}.{year}'])
        new_demand2020_cement.append(new_row)
        
    columns = ['node', 'value'] + years

    # Create DataFrame
    demand2020_cement = pd.DataFrame(new_demand2020_cement, columns=columns)


    # demand2010_cement = demand2010_cement.\
    #    join(gdp_growth.rename(columns={'Region':'node'}).set_index('node'), on='node')

    demand2020_cement.iloc[:, 2:] = (
        demand2020_cement.iloc[:, 2:]
        .div(demand2020_cement[2020], axis=0)
        .multiply(demand2020_cement["value"], axis=0)
    )

    # Do this if we have 2020 demand values for buildings
    # sp = get_spec()
    # if 'buildings' in sp['add'].set['technology']:
    #     val = get_scen_mat_demand("cement",scenario) # Mt in 2020
    #     print("Base year demand of {}:".format("cement"), val)
    #     # demand2020_cement['value'] = demand2020_cement['value'] - val['value']
    #     # Scale down all years' demand values by the 2020 ratio
    #     demand2020_cement.iloc[:,3:] =  demand2020_cement.iloc[:,3:].\
    #         multiply(demand2020_cement[2020]- val['value'], axis=0).\
    #         div(demand2020_cement[2020], axis=0)
    #     print("UPDATE {} demand for 2020!".format("cement"))
    #
    demand2020_cement = pd.melt(
        demand2020_cement.drop(["value"], axis=1),
        id_vars=["node"],
        var_name="year",
        value_name="value",
    )

    return demand2020_cement


def gen_data_cement(
    scenario: message_ix.Scenario, dry_run: bool = False
) -> dict[str, pd.DataFrame]:
    """Generate data for materials representation of cement industry."""
    # Load configuration
    context = read_config()
    config = read_config()["material"]["cement"]
    ssp = get_ssp_from_context(context)
    # Information about scenario, e.g. node, year
    s_info = ScenarioInfo(scenario)
    context.datafile = "Global_cement_MESSAGE.xlsx"#"Global_steel_cement_MESSAGE.xlsx"

    # Techno-economic assumptions
    data_cement = read_sector_data(scenario, "cement")#, "Global_cement_MESSAGE.xlsx")
    # Special treatment for time-dependent Parameters
    data_cement_ts = read_timeseries(scenario, "steel_cement", "Global_cement_MESSAGE.xlsx")
    tec_ts = set(data_cement_ts.technology)  # set of tecs with var_cost

    # List of data frames, to be concatenated together at end
    results = defaultdict(list)

    # For each technology there are different input and output combinations
    # Iterate over technologies

    yv_ya = s_info.yv_ya
    yv_ya = yv_ya.loc[yv_ya.year_vtg >= 1980]
    # Do not parametrize GLB region the same way
    nodes = nodes_ex_world(s_info.N)

    for t in [t for t in data_cement["technology"] if t in list(scenario.set('technology'))]: #config["technology"]["add"]:
        #t = t.id
        params = data_cement.loc[(data_cement["technology"] == t), "parameter"].unique()

        # Special treatment for time-varying params
        if t in tec_ts:
            common = dict(
                time="year",
                time_origin="year",
                time_dest="year",
            )

            param_name = data_cement_ts.loc[
                (data_cement_ts["technology"] == t), "parameter"
            ]

            for p in set(param_name):
                val = data_cement_ts.loc[
                    (data_cement_ts["technology"] == t)
                    & (data_cement_ts["parameter"] == p),
                    "value",
                ]
                # units = data_cement_ts.loc[
                #     (data_cement_ts["technology"] == t)
                #     & (data_cement_ts["parameter"] == p),
                #     "units",
                # ].values[0]
                mod = data_cement_ts.loc[
                    (data_cement_ts["technology"] == t)
                    & (data_cement_ts["parameter"] == p),
                    "mode",
                ]
                yr = data_cement_ts.loc[
                    (data_cement_ts["technology"] == t)
                    & (data_cement_ts["parameter"] == p),
                    "year",
                ]

                if p == "var_cost":
                    df = make_df(
                        p,
                        technology=t,
                        value=val,
                        unit="t",
                        year_vtg=yr,
                        year_act=yr,
                        mode=mod,
                        **common,
                    ).pipe(broadcast, node_loc=nodes)
                else:
                    rg = data_cement_ts.loc[
                        (data_cement_ts["technology"] == t)
                        & (data_cement_ts["parameter"] == p),
                        "region",
                    ]
                    df = make_df(
                        p,
                        technology=t,
                        value=val,
                        unit="t",
                        year_vtg=yr,
                        year_act=yr,
                        mode=mod,
                        node_loc=rg,
                        **common,
                    )

                results[p].append(df)

        # Iterate over parameters
        for par in params:
            # Obtain the parameter names, commodity,level,emission
            split = par.split("|")
            param_name = split[0]
            # Obtain the scalar value for the parameter
            val = data_cement.loc[
                ((data_cement["technology"] == t) & (data_cement["parameter"] == par)),
                "value",
            ]  # .values

            regions = data_cement.loc[
                ((data_cement["technology"] == t) & (data_cement["parameter"] == par)),
                "region",
            ]  # .values

            common = dict(
                year_vtg=yv_ya.year_vtg,
                year_act=yv_ya.year_act,
                # mode="M1",
                time="year",
                time_origin="year",
                time_dest="year",
            )

            for rg in regions:
                # For the parameters which inlcudes index names
                if len(split) > 1:
                    if (param_name == "input") | (param_name == "output"):
                        # Assign commodity and level names
                        com = split[1]
                        lev = split[2]
                        mod = split[3]

                        df = make_df(
                            param_name,
                            technology=t,
                            commodity=com,
                            level=lev,
                            value=val[regions[regions == rg].index[0]],
                            mode=mod,
                            unit="t",
                            node_loc=rg,
                            **common,
                        ).pipe(same_node)

                    elif param_name == "emission_factor":
                        # Assign the emisson type
                        emi = split[1]
                        mod = split[2]

                        df = make_df(
                            param_name,
                            technology=t,
                            value=val[regions[regions == rg].index[0]],
                            emission=emi,
                            mode=mod,
                            unit="t",
                            node_loc=rg,
                            **common,
                        )  # .pipe(broadcast, \
                        # node_loc=nodes))

                    else:  # time-independent var_cost
                        mod = split[1]
                        df = make_df(
                            param_name,
                            technology=t,
                            value=val[regions[regions == rg].index[0]],
                            mode=mod,
                            unit="t",
                            node_loc=rg,
                            **common,
                        )  # .pipe(broadcast, node_loc=nodes))

                # Parameters with only parameter name
                else:
                    df = make_df(
                        param_name,
                        technology=t,
                        value=val[regions[regions == rg].index[0]],
                        unit="t",
                        node_loc=rg,
                        **common,
                    )  # .pipe(broadcast, node_loc=nodes))

                if len(regions) == 1:
                    df["node_loc"] = None
                    df = df.pipe(broadcast, node_loc=nodes).pipe(same_node)

                results[param_name].append(df)



    # Create external demand param
    parname = "demand"
    df_demand = material_demand_calc.derive_demand("cement", scenario, ssp=ssp)
    results[parname].append(df_demand)

    # Add CCS as addon
    parname = "addon_conversion"

    technology_1 = ["clinker_dry_cement"]
    df_1 = make_df(
        parname, mode="M1", type_addon="dry_ccs_cement", value=1, unit="-", **common
    ).pipe(broadcast, node=nodes, technology=technology_1)

    technology_2 = ["clinker_wet_cement"]
    df_2 = make_df(
        parname, mode="M1", type_addon="wet_ccs_cement", value=1, unit="-", **common
    ).pipe(broadcast, node=nodes, technology=technology_2)

    results[parname].append(df_1)
    results[parname].append(df_2)

    # Concatenate to one data frame per parameter
    results = {par_name: pd.concat(dfs) for par_name, dfs in results.items()}

    results["initial_new_capacity_up"] = pd.concat(
        [
            calculate_ini_new_cap(
                df_demand=df_demand.copy(deep=True),
                technology="clinker_dry_ccs_cement",
                material="cement",
            ),
            calculate_ini_new_cap(
                df_demand=df_demand.copy(deep=True),
                technology="clinker_wet_ccs_cement",
                material="cement",
            ),
        ]
    )

    

    #replace_CH_with_CA_mock(results, "historical_activity")
    replace_CH_with_CA_Historical_activity(results, scale=False)
    replace_CH_with_CA_mock(results, "initial_new_capacity_up")
    replace_CH_with_CA_mock(results, "historical_new_capacity")

    replace_CH_with_CA_mock(results, "input", scale=False)
    replace_CH_with_CA_mock(results, "output", scale=False)
    replace_CH_with_CA_mock(results, "technical_lifetime", scale=False)

    replace_CH_with_CA_mock(results, "capacity_factor", scale=False)
    replace_CH_with_CA_mock(results, "inv_cost", scale=False)
    replace_CH_with_CA_mock(results, "fix_cost", scale=False)

    replace_CH_with_CA_mock(results, "emission_factor", scale=False)
    replace_CH_with_CA_mock(results, "growth_new_capacity_up", scale=False)

    demand_df = gen_mock_demand_cement(scenario)
    demand_df = demand_df[demand_df["node"] != "Canada"]

    demand_df['commodity'] = 'cement'
    demand_df['level'] = 'demand'
    demand_df['time'] = 'year'
    demand_df['unit'] = 't'
    results['demand'] = demand_df
    results['initial_new_capacity_up']['value'] = 1

    return results

def replace_CH_with_CA_mock(data, key, scale=True):
    # Your original historical activity DataFrame
    df = data[key]  # already loaded
    df_base = df.copy()

    # Dictionary of scaling factors
    province_factors = {
        #"Canada": 1.0,
        "Ontario": 0.28,
        "Quebec": 0.24,
        "Alberta": 0.15,
        "BritishColumbia": 0.12,
        "Manitoba": 0.05,
        "Saskatchewan": 0.06,
        "NovaScotia": 0.03,
        "NewBrunswick": 0.02,
        "NewfoundlandandLabrador": 0.02,
        "PrinceEdwardIsland": 0.01,
        "NorthwestTerritories": 0.02,
        "Yukon": 0.01,
        "Nunavut": 0.01,

    }

    # Create a new list of all scaled/provincial dataframes
    prov_df_list = []

    for province, factor in province_factors.items():
        temp = df_base.copy()
        temp["node_loc"] = province
        temp['node_origin'] = province
        if scale:
            temp["value"] = temp["value"] * factor * .0286
        prov_df_list.append(temp)

    # Combine all into one final dataframe
    df_canada_by_province = pd.concat(prov_df_list, ignore_index=True)
    data[key] = df_canada_by_province

def replace_CH_with_CA_Historical_activity(data, scale=False):
    key = "historical_activity"
    df = data[key]  # already loaded
    df_base = df.copy()

        # Dictionary of scaling factors
    province_factors = {
        #"Canada": 1.0,
        "Ontario": 0.5,
        "Quebec": 0.17,
        "Alberta": 0.17,
        "BritishColumbia": 0.16,
        "Manitoba": 0,
        "Saskatchewan": 0,
        "NovaScotia": 0,
        "NewBrunswick": 0,
        "NewfoundlandandLabrador": 0,
        "PrinceEdwardIsland": 0,
        "NorthwestTerritories": 0,
        "Yukon": 0,
        "Nunavut": 0,

    }

    # Create a new list of all scaled/provincial dataframes
    prov_df_list = []

    for province, factor in province_factors.items():
        temp = df_base.copy()
        temp["node_loc"] = province
        temp['node_origin'] = province
        if scale:
            temp["value"] = temp["value"] * factor * .0286
        else:
            temp["value"] = temp["value"] * factor
        prov_df_list.append(temp)

    # Combine all into one final dataframe
    df_canada_by_province = pd.concat(prov_df_list, ignore_index=True)
    data[key] = df_canada_by_province

DATA_FUNCTIONS_1 = [
    # # gen_data_buildings,
    # gen_data_methanol_new,
    # gen_all_NH3_fert,
    # # gen_data_ammonia, ## deprecated module!
    # gen_data_generic,
    # gen_data_steel,
]
DATA_FUNCTIONS_2 = [
    gen_data_cement,
    # gen_data_petro_chemicals,
    # gen_data_power_sector,
    # gen_data_aluminum,
]

# add as needed/implemented
SPEC_LIST = [
    "generic",
    "common",
    "steel",
    "cement",
    # "aluminum",
    # "petro_chemicals",
    # "buildings",
    # "power_sector",
    # "fertilizer",
    # "methanol",
]


# Try to handle multiple data input functions from different materials
def add_data_1(scenario, dry_run=False):
    """Populate `scenario` with MESSAGEix-Materials data."""
    # Information about `scenario`
    info = ScenarioInfo(scenario)

    # Check for two "node" values for global data, e.g. in
    # ixmp://ene-ixmp/CD_Links_SSP2_v2.1_clean/baseline
    if {"World", "R11_GLB"} < set(info.set["node"]):
        log.warning("Remove 'R11_GLB' from node list for data generation")
        info.set["node"].remove("R11_GLB")
    if {"World", "R12_GLB"} < set(info.set["node"]):
        log.warning("Remove 'R12_GLB' from node list for data generation")
        info.set["node"].remove("R12_GLB")

    for func in DATA_FUNCTIONS_1 + DATA_FUNCTIONS_2:
        # Generate or load the data; add to the Scenario
        log.info(f"from {func.__name__}()")
        print(f"from {func.__name__}()")
        data = func(scenario)
        data['input'] = data['input'][data['input']['node_loc'] == data['input']['node_origin']]
        data['output'] = data['output'][data['output']['node_loc'] == data['output']['node_dest']]
        # if "SSP_dev" in scenario.model:
        #     if "emission_factor" in list(data.keys()):
        #         data.pop("emission_factor")
        add_par_data(scenario, data, dry_run=dry_run)

    log.info("done")


def add_data_2(scenario, dry_run=False):
    """Populate `scenario` with MESSAGEix-Materials data."""
    # Information about `scenario`
    info = ScenarioInfo(scenario)

    # Check for two "node" values for global data, e.g. in
    # ixmp://ene-ixmp/CD_Links_SSP2_v2.1_clean/baseline
    if {"World", "R11_GLB"} < set(info.set["node"]):
        log.warning("Remove 'R11_GLB' from node list for data generation")
        info.set["node"].remove("R11_GLB")
    if {"World", "R12_GLB"} < set(info.set["node"]):
        log.warning("Remove 'R12_GLB' from node list for data generation")
        info.set["node"].remove("R12_GLB")

    for func in DATA_FUNCTIONS_2:
        # Generate or load the data; add to the Scenario
        log.info(f"from {func.__name__}()")
        # TODO: remove this once emission_factors are back in SSP_dev
        data = func(scenario)
        # if "SSP_dev" in scenario.model:
        #     if "emission_factor" in list(data.keys()):
        #         data.pop("emission_factor")
        add_par_data(scenario, data, dry_run=dry_run)

    log.info("done")


def build(
    scenario: message_ix.Scenario, old_calib: bool, iea_data_path=None
) -> message_ix.Scenario:
    """Set up materials accounting on `scenario`."""

    # Get the specification
    # Apply to the base scenario
    spec = get_spec()

    if "water_supply" not in list(scenario.set("level")):
        scenario.check_out()
        # add missing water tecs
        scenario.add_set("technology", "extract__freshwater_supply")
        scenario.add_set("level", "water_supply")
        scenario.add_set("commodity", "freshwater_supply")

        water_dict = pd.read_excel(
            package_data_path("material", "other", "water_tec_pars.xlsx"),
            sheet_name=None,
        )
        for par in water_dict.keys():
            scenario.add_par(par, water_dict[par])
        scenario.commit("add missing water tecs")

    apply_spec(scenario, spec, add_data_1, fast=True)  # dry_run=True
    if "SSP_dev" not in scenario.model:
        engage_updates._correct_balance_td_efficiencies(scenario)
        #engage_updates._correct_coal_ppl_u_efficiencies(scenario)
        engage_updates._correct_td_co2cc_emissions(scenario)
    # spec = None
    # apply_spec(scenario, spec, add_data_2)
    from message_ix_models import ScenarioInfo

    s_info = ScenarioInfo(scenario)
    nodes = s_info.N

    # Adjust exogenous energy demand to incorporate the endogenized sectors
    # Adjust the historical activity of the useful level industry technologies
    # Coal calibration 2020
    add_ccs_technologies(scenario)
    if old_calib:
        modify_demand_and_hist_activity(scenario)
    else:
        modify_baseyear_bounds(scenario)

        last_hist_year = scenario.par("historical_activity")["year_act"].max()

        #seems to be for chemicals only
        #modify_industry_demand(scenario, last_hist_year, iea_data_path)

        #it refrences a demand file that I don't have
        #add_new_ind_hist_act(scenario, [last_hist_year], iea_data_path)

        #uncomment
        add_elec_i_ini_act(scenario)
        #uncomment
        add_emission_accounting(scenario)

        # scenario.commit("no changes")

    #refrences messing data for China cement bounds    
    #add_coal_lowerbound_2020(scenario)
    #add_cement_bounds_2020(scenario)

    # Market penetration adjustments
    # NOTE: changing demand affects the market penetration
    # levels for the enduse technologies.
    # FIXME: context.ssp only works for SSP1/2/3 currently missing SSP4/5

    # Error with nodes
    # calibrate_UE_gr_to_demand(
    #     scenario,
    #     s_info,
    #     data_path=package_data_path("material"),
    #     ssp="SSP2",
    #     region=identify_nodes(scenario),
    # )

    calibrate_UE_share_constraints(scenario, s_info)

    # scenario.check_out()
    # input_df = scenario.par('input')
    # scenario.remove_par("input")
    # scenario.commit("input processing commit")
    # input_df = input_df[input_df['node_loc'] == input_df['node_origin']]
    # scenario.add_par("input",input_df)

    # scenario.commit("input processing commit")

    # scenario.check_out()

    # output_df = scenario.par('output')
    # scenario.remove_par("output")
    # scenario.commit("output processing commit")
    # output_df = output_df[output_df['node_loc'] == output_df['node_dest']]
    # scenario.add_par("output", output_df)

    # scenario.commit("output processing commit")

    # Electricity calibration to avoid zero prices for CHN.
    # if "R12_CHN" in nodes:
    #     add_elec_lowerbound_2020(scenario)

    # i_feed demand is zero creating a zero division error during MACRO calibration
    scenario.check_out()
    scenario.remove_set("sector", "i_feed")
    scenario.commit("i_feed removed from sectors.")

    df = scenario.par(
        "bound_activity_lo",
        filters={"node_loc": "R12_RCPA", "technology": "sp_el_I", "year_act": 2020},
    )
    scenario.check_out()
    scenario.remove_par("bound_activity_lo", df)
    scenario.commit("remove sp_el_I min bound on RCPA in 2020")
    print("HEYYYY!")
    return scenario


def get_spec() -> Mapping[str, ScenarioInfo]:
    """Return the specification for materials accounting."""
    require = ScenarioInfo()
    add = ScenarioInfo()
    remove = ScenarioInfo()

    # Load configuration
    # context = Context.get_instance(-1)
    context = read_config()

    # Update the ScenarioInfo objects with required and new set elements
    for type in SPEC_LIST:
        for set_name, config in context["material"][type].items():
            # for cat_name, detail in config.items():
            # Required elements
            require.set[set_name].extend(config.get("require", []))

            # Elements to add
            add.set[set_name].extend(config.get("add", []))

            # Elements to remove
            remove.set[set_name].extend(config.get("remove", []))

    return dict(require=require, add=add, remove=remove)

