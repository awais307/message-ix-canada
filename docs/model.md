# Model

The `model` directory in MESSAGEix-Canada houses the core components of the model structure itself. This includes all the configurations and setup scripts necessary for defining how the model operates.

The model is set up and initialized using the `setup_scenario` method of the `model_MSG` class, which reads in a configuration file (`config.toml`) for a given scenario. This function initializes the MESSAGEix scenario object and performs various preprocessing steps such as processing historical data and adding hydrogen shares.

Ensure that the configurations within the `config.toml` are correctly defined according to your scenario requirements before running the model.

## Model Classes

### Model_MSG

The `model_MSG` class is a wrapper for the MESSAGEix framework, which handles initialization and execution of the model. It also contains methods for performing various calculations on the results from the model. This includes calculating emissions based on historical data, adding hydrogen shares to the energy mix, adding new technologies to the energy grid, and adjusting the demand curves in the model according to GDP and population growth.

### Plotter_MSG

The `plotter_MSG` class is a wrapper for the MESSAGEix model, which handles the plotting functionalities of the model. It contains methods for creating structured dataframes which are used for visualizing results from the model.

## Utilities and Other Scripts

Additional scripts are provided by the `utils.py` file and other files found inside the "model" folder. In the utility's script you can find nscripts for cloning an exisitng model, validating the configuration of a scenario, and an internal mapper function which creates a range of years from a vintage year to all the activity years after.

## Emissions Calculation

There are two types of emissions accounting in the model. One is top-down (extraction level) and the other one bottom-up which is process level. The top-down emission accounting is used for implementing carbon prices and bounds on the emission and it is parameterized in the realtion `CO2_emission`.For `CO2_emission`, the positive values are extraction and import technologies and the negative values are mitigation technologies (e.g CCS). The technologies in the relation `CO2_emission` then has the `emission_factor` and it gets written in to the emission type `TCE`. When we put a boudn on `TCE` , then we can see above which technologies are contributing. The CH4, N2O and HFCs are just technological groupings. We do not have land use emissions parameterized here.

The emission factors for the fuels can be found here: [https://docs.messageix.org/projects/global/en/latest/emissions/message/index.html](https://docs.messageix.org/projects/global/en/latest/emissions/message/index.html) . Hence the value of emission factor in MESSAGEix-Canada is base on input of the relevant power plants. Eg for coal power plant, this value in CO2_CC relation needs to be multiplied by input value of coal_ppl to get the emission factor.

1 tonne CO2 (or CO2e) emissions = 1 tonne × 12/44 = 0.27 tonnes carbon emissions (the other 0.73 tonnes were oxygen).

The relation `CO2_cc` is not what is used for emission bound.

Note that model emission are C-equivalent and not CO2 equivalent.
Emission factors for technologies itself are not wrong.

Coal ppl Example just for fuel related emission factors.

Relation - CO2_cc value is 2.11979
Input value or efficiency of coal power plant = 1/2.63158 = 0.379
Emission factor of coal ppl = 2.11979 * 0.379 = 0.8044 tC/kWyr

we need to convert the bounds to tonne of carbon -
