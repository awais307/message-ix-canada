# Installation Instructions

This section provides a step-by-step guide to installing and setting up MESSAGEix-Canada on your local machine. The process involves setting up a Python environment using `conda`, installing the necessary packages, and configuring the model.

## Prerequisites

Before you begin, ensure that you have the following installed on your system:

- [Miniconda or Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) (for managing Python environments)
- Git (for cloning the repository)

## Step 1: Clone the Repository

First, clone the MESSAGEix-Canada repository from GitLab:

```bash
git clone https://gitlab.com/sesit/message-ix
cd message-ix
```

## Step 2: Set up the Conda Environment

The project includes an environment.yml file that lists all the necessary dependencies. Create a new Conda environment using this file:
```bash
conda env create -f environment.yml
```

## Step 3: Activate the Environment

Activate the newly created environment:
```bash
conda activate messageix-canada
```

## Step 4: Verify the Installation

To verify that the installation was successful, you can try importing MESSAGEix-Canada in Python:

```
message-ix show-versions
```

## Important Step for Open-source Solvers:

To run MESSAGE Canada with open-source solvers like CBC, or GLPK, simply change the LP option from MESSAGE's auxiliary settings file in: your message_ix Python package folder. This can be found under `anaconda3/envs/messageix-canada/lib/python3.12/site-packages/message_ix/model/MESSAGE/auxiliary_settings.gms`. For further clarity, you can read more about the auxiliary settings file [here](https://github.com/iiasa/message_ix/issues/576) and also [here](https://github.com/iiasa/message_ix/discussions/794).