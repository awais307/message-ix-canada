# import all callback, plot and processing functions
from plotting_utils.callbacks import (
    emissions as emissions_callbacks,
    capital_cost as capital_cost_callbacks,
    total_cost as total_cost_callbacks,
    capacity_additions as capacity_additions_callbacks,
    capacity as capacity_callbacks,
    primary_energy as primary_energy_callbacks,
    secondary_energy as secondary_energy_callbacks,
    final_energy as final_energy_callbacks,
    useful_energy as useful_energy_callbacks,
    overview as overview_callbacks
)

from plotting_utils.processing_scripts import (
    emissions as emissions_processing,
    capital_cost as capital_cost_processing,
    total_cost as total_cost_processing,
    capacity_additions as capacity_additions_processing,
    capacity as capacity_processing,
    primary_energy as primary_energy_processing,
    secondary_energy as secondary_energy_processing,
    final_energy as final_energy_processing,
    useful_energy as useful_energy_processing,
    overview as overview_processing
)

from plotting_utils.visualization_scripts import (
    emissions as emissions_viz,
    total_cost as total_cost_viz,
    capital_cost as capital_cost_viz,
    capacity_additions as capacity_additions_viz,
    capacity as capacity_viz,
    primary_energy as primary_energy_viz,
    secondary_energy as secondary_energy_viz,
    final_energy as final_energy_viz,
    useful_energy as useful_energy_viz,
    overview as overview_viz
)



# link all callbacks
def link(app):
    emissions_callbacks.link(app)
    capital_cost_callbacks.link(app)
    total_cost_callbacks.link(app)
    capacity_additions_callbacks.link(app)
    capacity_callbacks.link(app)
    primary_energy_callbacks.link(app)
    secondary_energy_callbacks.link(app)
    final_energy_callbacks.link(app)
    useful_energy_callbacks.link(app)
    overview_callbacks.link(app)


# function to check which processing function to use
def check(df):
    plots = []
    if emissions_processing.check(df):
        plots.append('emissions')
    if capital_cost_processing.check(df):
        plots.append('capital_cost')
    if total_cost_processing.check(df):
        plots.append('total_cost')
    if capacity_additions_processing.check(df):
        plots.append('capacity_additions')
    if capacity_processing.check(df):
        plots.append('capacity')
    if primary_energy_processing.check(df):
        plots.append('primary_energy')
    if secondary_energy_processing.check(df):
        plots.append('secondary_energy')
    if final_energy_processing.check(df):
        plots.append('final_energy')
    if useful_energy_processing.check(df):
        plots.append('useful_energy')
    if overview_processing.check(df):
        plots.append('overview')
    return plots


def process(df, checked):
    scenario_name = df['scenario'].unique()[0]
    dfs = {}
    if 'emissions' in checked:
        dfs['emissions'] = emissions_processing.process({scenario_name: df})
    if 'capital_cost' in checked:
        dfs['capital_cost'] = capital_cost_processing.process({scenario_name: df})
    if 'total_cost' in checked:
        dfs['total_cost'] = total_cost_processing.process({scenario_name: df})
    if 'capacity_additions' in checked:
        dfs['capacity_additions'] = capacity_additions_processing.process({scenario_name: df})
    if 'capacity' in checked:
        dfs['capacity'] = capacity_processing.process({scenario_name: df})
    if 'primary_energy' in checked:
        dfs['primary_energy'] = primary_energy_processing.process({scenario_name: df})
    if 'secondary_energy' in checked:
        dfs['secondary_energy'] = secondary_energy_processing.process({scenario_name: df})
    if 'final_energy' in checked:
        dfs['final_energy'] = final_energy_processing.process({scenario_name: df})
    if 'useful_energy' in checked:
        dfs['useful_energy'] = useful_energy_processing.process({scenario_name: df})
    if 'overview' in checked:
        dfs['overview'] = overview_processing.process({scenario_name: df})
    return dfs


def get_views(dfs):
    plots = {}
    for viz, df in dfs.items():
        if viz == 'emissions':
            plots['emissions'] = emissions_viz.plot(df, 0)[-1]
        if viz == 'capital_cost':
            plots['capital_cost'] = capital_cost_viz.plot(df, 0)[-1]
        if viz == 'total_cost':
            plots['total_cost'] = total_cost_viz.plot(df, 0)[-1]
        if viz == 'capacity_additions':
            plots['capacity_additions'] = capacity_additions_viz.plot(df, 0)[-1]
        if viz == 'capacity':
            plots['capacity'] = capacity_viz.plot(df, 0)[-1]
        if viz == 'primary_energy':
            plots['primary_energy'] = primary_energy_viz.plot(df, 0)[-1]
        if viz == 'secondary_energy':
            plots['secondary_energy'] = secondary_energy_viz.plot(df, 0)[-1]
        if viz == 'final_energy':
            plots['final_energy'] = final_energy_viz.plot(df, 0)[-1]
        if viz == 'useful_energy':
            plots['useful_energy'] = useful_energy_viz.plot(df, 0)[-1]
        if viz == 'overview':
            plots['overview'] = overview_viz.plot(df, 0)[-1]
    return plots

import dash
from dash import html, dcc
import pandas as pd

# create the dash app
app = dash.Dash(__name__)

file = 'MESSAGE_CANADA_provincial_baseline.csv'
df = pd.read_csv(file)

# drop first column
df = df.drop(columns=df.columns[0])


# make all columns lowercase
df.columns = [col.lower() for col in df.columns]
df.model = 'MESSAGEix-Canada'

checked = check(df)
dfs = process(df, checked)
views = get_views(dfs)

# add tabs to the app where the plots will be displayed
app.layout = html.Div([
    dcc.Tabs([
        dcc.Tab(label='Emissions', children=[
            html.Div([
                views['emissions']
            ])
        ]),
        dcc.Tab(label='Capital Cost', children=[
            html.Div([
                views['capital_cost']
            ])
        ]),
        dcc.Tab(label='Total Cost', children=[
            html.Div([
                views['total_cost']
            ])
        ]),
        dcc.Tab(label='Capacity Additions', children=[
            html.Div([
                views['capacity_additions']
            ])
        ]),
        dcc.Tab(label='Capacity', children=[
            html.Div([
                views['capacity']
            ])
        ]),
        dcc.Tab(label='Primary Energy', children=[
            html.Div([
                views['primary_energy']
            ])
        ]),
        dcc.Tab(label='Secondary Energy', children=[
            html.Div([
                views['secondary_energy']
            ])
        ]),
        dcc.Tab(label='Final Energy', children=[
            html.Div([
                views['final_energy']
            ])
        ]),
        dcc.Tab(label='Useful Energy', children=[
            html.Div([
                views['useful_energy']
            ])
        ]),
        dcc.Tab(label='Overview', children=[
            html.Div([
                views['overview']
            ])
        ]),
    ])
])

# save all views to a file
for viz, view in views.items():
    print(viz, 'to html')
    view.figure.write_html(f'{viz}.html')

# start app
if __name__ == '__main__':
    app.run_server(debug=True)





