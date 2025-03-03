# Installation Instructions

This section provides a detailed guide to installing and setting up **MESSAGEix-Canada** on your local machine. The setup process involves configuring a **Python environment**, installing necessary dependencies, and ensuring that all required external tools are properly installed.

## **Prerequisites**

Before proceeding with the installation, ensure you have the following dependencies installed on your system:

- **[Miniconda or Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)** – Required for managing Python environments.
- **[Git](https://git-scm.com/downloads)** – Needed to clone the MESSAGEix-Canada repository.
- **[GAMS](https://www.gams.com/download/)** – Required for running MESSAGEix models.

## **Setting Up MESSAGEix-Canada**

### **1. Clone the Repository**

Start by cloning the MESSAGEix-Canada repository from GitLab and navigating to the project directory:

```bash
git clone https://gitlab.com/sesit/message-ix
cd message-ix
```

### **2. Configure the Conda Environment**

Create a new isolated **Anaconda** environment to ensure all dependencies work correctly:

```bash
conda create -n messageix-canada python=3.12
```

### **3. Activate the Environment**

Once created, activate the environment:

```bash
conda activate messageix-canada
```

### **4. Install Required Packages**

Install the necessary Python dependencies:

```bash
pip install -e .
```

### **5. Verify the Installation**

To confirm that MESSAGEix-Canada is correctly installed, execute the following command:

```bash
message-ix show-versions
```

If the command runs successfully, your setup is complete.

## **Configuring Open-Source Solvers**

MESSAGEix-Canada can be executed using open-source solvers such as **CBC** or **GLPK**. To enable these solvers, modify the **auxiliary settings file** located in:

```
anaconda3/envs/messageix-canada/lib/python3.12/site-packages/message_ix/model/MESSAGE/auxiliary_settings.gms
```

For further details, refer to the discussions [here](https://github.com/iiasa/message_ix/issues/576) and [here](https://github.com/iiasa/message_ix/discussions/794).

A collection of verified **open-source solvers** for **GAMS** is available via the **COIN-OR Foundation**. The latest release and installation instructions for GAMSlinks can be found [here](https://github.com/coin-or/GAMSlinks/releases).

### **Solver Performance Benchmark for MESSAGEix-Canada**

Below are benchmarks for different solvers tested with MESSAGEix-Canada:

- **CBC:** 1 min 20 sec
- **Soplex:** 12 min 42 sec
- **HiGHS:** 2 min 30 sec
- **IPOPT:** 15+ minutes

## **Installing GAMSlinks and Solvers**

To install open-source solvers via **GAMSlinks**, follow these steps:

1. **Download the latest release**:

   - **Windows:** Download and unzip `GAMSlinks-windows.zip`.
   - **Linux:** Download `GAMSlinks-linux.tar.bz2` and extract it using:
     ```bash
     tar -xvjf GAMSlinks-linux.tar.bz2
     ```
   - **Mac OS:** Download `GAMSlinks-macos.tar.bz2` and extract it using:
     ```bash
     tar -xvjf GAMSlinks-macos.tar.bz2
     ```
2. **Configure the solver package:**

   ```bash
   configure
   make
   make install
   ```
3. **Update GAMS configuration:**
   Modify the `gamsconfig.yaml` file and add it to your **GAMS path**. Refer to the official [GAMS documentation](https://www.gams.com/latest/docs/UG_STANDARD_LOCATIONS.html) for details.

### **Using CBC Solver**

We recommend using the **CBC solver**, which can be installed via **Coin-OR**. Follow the installation guide in the [README](https://github.com/coin-or/Cbc/blob/master/README.md#download).

For further troubleshooting or known installation issues, refer to the **official installation guide** in the [MESSAGEix documentation](https://docs.messageix.org/en/latest/install.html).
