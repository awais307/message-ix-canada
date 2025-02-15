# Installation Instructions

This section provides a step-by-step guide to installing and setting up MESSAGEix-Canada on your local machine. The process involves setting up a Python environment using `conda`, installing the necessary packages, and configuring the model.

## Prerequisites

Before you begin, ensure that you have the following installed on your system:

- [Miniconda or Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) (for managing Python environments)
- [Git](https://git-scm.com/downloads) (for cloning the repository)
- [GAMS](https://www.gams.com/download/) (for modelling with MESSAGE-ix models)

## Step 1: Clone the Repository

First, clone the MESSAGEix-Canada repository from GitLab:

```bash
git clone https://gitlab.com/sesit/message-ix
cd message-ix
```

## Step 2: Set up the Conda Environment

Create a new Anaconda environment:

```bash
conda create -n messageix-canada python=3.12
```

## Step 3: Activate the Environment

Activate the newly created environment:

```bash
conda activate messageix-canada
```

## Step 4: Install the Packages

Install all necessary packages from MESSAGEix Canada using `pip`

```bash
pip install -e .
```

## Step 5: Verify the Installation

To verify that the installation was successful, you can try importing MESSAGEix-Canada in Python:

```bash
message-ix show-versions
```

## Important Step for Open-source Solvers

To run MESSAGE Canada with open-source solvers like CBC, or GLPK, simply change the LP option from MESSAGE's auxiliary settings file in: your message_ix Python package folder. This can be found under `anaconda3/envs/messageix-canada/lib/python3.12/site-packages/message_ix/model/MESSAGE/auxiliary_settings.gms`. For further clarity, you can read more about the auxiliary settings file [here](https://github.com/iiasa/message_ix/issues/576) and also [here](https://github.com/iiasa/message_ix/discussions/794).

A collection of verified open-source solvers for [GAMS](https://www.gams.com/) was created by the COIN-OR Foundation. You can access the latest release of their GAMSlinks package as well as the installation instructions [here](https://github.com/coin-or/GAMSlinks/releases). See a summary of the installation instructions in the next section. The bech-mark of these  solvers for MESSAGE Canada is as follows:

- CBC: 1 min 20 sec
- Soplex: 12 min 42 sec
- Highs: 2 min 30 sec
- IPOPT:  15+ minutes

## GAMSlinks and Solvers Installation

There are multiple solvers which can be used with GAMS to solve models. From open-source to commercial options, MESSAGE-ix can be solved with many of the options available.

We recommend the use of the CBC solver, which can be installed as described in Coin-OR's [README](https://github.com/coin-or/Cbc/blob/master/README.md#download). The GAMSlinks package, which includes all available solvers from Coin-OR that can be used with GAMS, is another option for downloading solvers. To install the solvers through GAMSlinks follow these steps (GAMS must already be installed):

1. Download the [latest release](https://github.com/coin-or/GAMSlinks/releases)
   - Windows: download the `GAMSlinks-windows.zip ` file and unzip
   - Linux: download the  ` GAMSlinks-linux.tar.bz2 ` file and unzip with `tar -xvjf GAMSlinks-linux.tar.bz2`
   - Mac OS: download the `GAMSlinks-macos.tar.bz2` and unzip it with `tar -xvjf GAMSlinks-macos.tar.bz2`
2. Configure links by running:
    
    ```bash
    configure
    make
    make install
    ```
3. Update the `gamsconfig.yaml` file and add it to your [GAMS path](https://www.gams.com/latest/docs/UG_STANDARD_LOCATIONS.html). You can do this by copying the file into the locations GAMS will use to look for a configuration file

The `opt<SOLVER_NAME>.md` files for each solver have more information on some options you can include into the `auxiliary_settings.gms` file from the MESSAGE installation.

