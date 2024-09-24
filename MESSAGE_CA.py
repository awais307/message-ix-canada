import os
from pathlib import Path
import click
from model.message_phases import model, Plotter_MSG

# Options for the CLI
@click.command()
@click.option('--scenario', default='baseline', help='Build the scenario folder name.')
@click.option('--solve', default=False, is_flag=True, help='Solve the model or not.')
@click.option('--debug', default=False, is_flag=True, help='Enable debug mode or not.')
@click.option('--report', default=False, is_flag=True, help='Generate report or not.')
@click.option('--plot', default=False, is_flag=True, help='Generate plots')

def messagerun(scenario, solve, debug, report, plot):
    """
    This function executes the MESSAGEix-Canada model workflow based on command-line inputs.
    """
    # Print the chosen options
    print(f"Running scenario: {scenario}")
    print(f"Solve: {solve}, Debug: {debug}, Report: {report}")

    # Create model instance
    msg1 = model(scenario_name=scenario)

    # Set up model with the selected scenario
    platform, msg_scenario, msg_folder = msg1.setup_scenario()

    # Plotter
    msg_plt = Plotter_MSG(msg_scenario)
    nodes = msg_scenario.set("node")[2:]
    #TODO Do we need plots_df here ?
    plots_df = msg_plt.plotter(
        case="test", nodeloc= nodes, path="./", yr_min=2020, yr_max=2060
    )

    # Remove the model solution (if any) and check out the scenario
    try:
        msg_scenario.remove_solution()
    except ValueError as e:
        print(e)
    msg_scenario.check_out()

    # Implement solve logic
    if solve:
        print("Solving the model...")
        #TODO Add solve method here
        #TODO this would need a bit of adjustment on how we take solve.
        # In future, one could use the messagerun function and cal it manually in notebook if required.

    # Debug mode logic
    if debug:
        print("Debug mode enabled")
        #TODO Add debug specific logs here

    # Report generation logic
    if report:
        print("Generating report...")
        #TODO Add report generation logic here


if __name__ == "__main__":
    messagerun()
