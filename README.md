# MESSAGEix-Canada
This repository contains MESSAGEix Canada. The provincial-scale model is currently being developed.

## Installation/Getting Started
MESSAGEix can be installed by following the instructions [here](https://docs.messageix.org/en/stable/install.html). The documentation for MESSAGEix contains most of the important information for getting started, including some useful tutorials which are available [here](https://github.com/iiasa/message_ix/tree/main/tutorial).

## Documentation

The following is meant to get a future co-op student up to speed on the provincial MESSAGEix model, and lists all necessary skills to ensure a smooth transition. The section title have links to relevant documentation when applicable.



### Pre-Requisites


To add data to the MESSAGEix model,the data should be in the `model-readable`  format. The formatted data required to solve a baseline scenario is located under 'scenarios/common/'. If new data is being used for a specific scenario, create and name a scenario folder within 'scenarios', and ensure the file is named appropriately according to the inputs of MESSAGEix Canada. Place the new data and a configuration file within the scenario and fill in config.toml according to the specifications of the scenario.

### Running the Model

To run the model for the baseline scenario, navigate to the parent directory of your repository. Then run the main model runner using the following command: python MESSAGE-CANADA.py baseline. If you have already created and configured a custom scenario, you can instead use: python MESSAGE-CANADA.py <scenario_name> where <scenario_name> would be replaced by the name of the folder you created within the 'scenarios' folder.

### Interacting with the Model After Solving

### [MESSAGEix](https://docs.messageix.org/en/stable/index.html)

The following are the most important things to know (many are covered in the tutorials linked above):

- How to create a MESSAGEix scenario and add parameters to it
- The format of MESSAGEix parameter dataframes
- How to read in parameters from an excel sheet (these files are found in data/MESSAGE\_CA\_\_TEST\_\_V#.xlsx)
- What the parameter names mean in MESSAGEix ([See here](https://docs.messageix.org/projects/models/en/stable/pkg-data/codelists.html))

### Python

An introductory level programming experience with Python can work to kick off the work. 
Specific things which are important for this project include:
- Python's [pandas](https://pandas.pydata.org/docs/) and [pyam](https://pyam-iamc.readthedocs.io/en/stable/) packages
- The basics of [matplotlib](https://matplotlib.org/stable/api/index)
- Creating python environments and installing packages (I used [anaconda](https://docs.anaconda.com/anaconda/user-guide/getting-started/) for this)
- Knowledge of a python IDE (this is mostly a personal preference, although normally [jupyter notebooks](https://jupyter.readthedocs.io/en/latest/index.html) are useful as it displays dataframes in-line in a format that is more legible than other IDEs)

#### [pandas](https://pandas.pydata.org/pandas-docs/stable/getting_started/index.html\#getting-started)

Important things to know include:

- The basics of pandas dataframes
    - Reading .csv and .xlsx files
    - The [various methods](https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html) of filtering and indexing dataframes

#### [pyam](https://pyam-iamc.readthedocs.io/en/stable/index.html)

If learning how to use pandas proves too much of a hassle initially, pyam is a useful package which simplifies some of it's operations. The website linked above has useful tutorials that can be completed quickly. Important things to know include:

- The format of pyam dataframes (these are specifically designed to organize data from integrated assessment models)
- Filtering in pyam
- pyam's downscaling function

### Excel

Basic knowledge of Excel (or a similar spreadsheet program) is fine.

### [git](https://docs.gitlab.com/ee/gitlab-basics/)

The most important things to know are:

- How to clone a repository, create a branch, and push/pull to/from the main repository
- How to create an ssh key to grant authentication to update the main repository
- How to create a .gitignore file, which tells git which files in the clone do not need to be uploaded to the main repository (there are useful templates found [here](https://github.com/github/gitignore))

### Contributors: 
- Muhammad Awais 
- Noah Leverton 
