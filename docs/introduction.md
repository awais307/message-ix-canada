# Introduction to MESSAGEix-Canada

Welcome to the MESSAGEix-Canada documentation. MESSAGEix-Canada is a customized energy systems model developed using the MESSAGEix modeling framework, tailored to capture the unique energy dynamics of Canada's provinces and territories. This model offers high-resolution insights into the regional energy supply and demand, accounting for the specific technological, geographical, and policy-related factors that influence energy systems across Canada.

## Key Features of MESSAGEix-Canada

### Provincial-Level Granularity
Unlike traditional energy models that operate at a national level, MESSAGEix-Canada provides detailed energy system representations at the provincial level. This allows for more accurate modeling of energy flows, resource availability, and technology deployment within each province, taking into account local energy policies and market conditions.

### Hydrogen Integration
As part of Canada's strategy to reduce greenhouse gas emissions, hydrogen plays a crucial role. MESSAGEix-Canada integrates hydrogen use across various sectors, including industry, transportation, and residential applications. The model includes functionality to adjust hydrogen shares in energy consumption and production, reflecting Canada's growing emphasis on hydrogen as a clean energy source.

### Historical Data Integration
The model incorporates historical activity data for calibration and validation, ensuring that it accurately reflects past energy trends and can be used to project future scenarios. The `update_historical_activity` function automates the integration of historical data into the model, allowing for efficient updates and refinements.

### Scenario-Based Analysis
MESSAGEix-Canada is designed to facilitate scenario-based analysis, enabling users to explore various energy futures under different assumptions. Users can easily configure and run scenarios using TOML configuration files, making it straightforward to test the impacts of different policies, technologies, and external factors on the energy system.

### Reporting and Exporting Capabilities
The model includes robust post-processing tools to generate detailed reports and export results to Excel. This functionality supports transparent and accessible dissemination of modeling results, making it easier for policymakers, researchers, and stakeholders to interpret and utilize the findings.

### Open-Source and Collaborative
MESSAGEix-Canada is an open-source project, encouraging collaboration among researchers, policymakers, and other stakeholders interested in Canada's energy future. The open-source nature of the project allows for continuous improvement and adaptation of the model to new data, policies, and technologies.

## Getting Started

To get started with MESSAGEix-Canada, users can follow the instructions in the 'Installation Instructions' section. This section provides step-by-step guidance on setting up the modeling environment, configuring scenarios, and running simulations.
