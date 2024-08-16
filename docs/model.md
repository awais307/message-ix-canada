# Model

The `model` directory in MESSAGEix-Canada houses the core components of the model structure itself. This includes all the configurations and setup scripts necessary for defining how the model operates. 

The model is set up and initialized using the `setup_scenario` function, which reads in a configuration file (`config.toml`) for a given scenario. This function initializes the MESSAGEix scenario object and performs various preprocessing steps such as processing historical data and adding hydrogen shares.

Ensure that the configurations within the `config.toml` are correctly defined according to your scenario requirements before running the model.
