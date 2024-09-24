# Output Based Pricing System Calculation

This script processes the Output Based Pricing System (OBPS) as an addition to the fixed costs of selected technologies. The technologies and their Relations Activity are adjustable and can be modified as needed.

## Federal OBPS (Initial Version)

The Federal OBPS is designed to calculate the federal carbon pollution pricing system, which includes a regulatory charge on fuel (the federal fuel charge). This function modifies the scenario's fixed costs based on emissions intensity and carbon pricing.

The processing is carried out using the relation known as `CO2_Emission`, which represents the emissions of CO2 during the extraction phase (measured as carbon, in tons C/kWyr).

The `federal_obps.py` policy begins by reading the `data_CA_provincial_reference_v1.xlsx` file. It then filters this dataset based on the defined technologies, relation, and relevant columns, which are adjustable. The filtered dataset is written as a new CSV file to facilitate calculations. At this step, it filters extraction technologies and selects the `CO2_Emission` relation. 

In the federal calculation, the values for the `CO2_Emission` relations are uniform across all provinces; therefore, the script selects only one province, such as Alberta, to implement filtering for efficiency. This approach will apply to all provinces and related technologies.

**Carbon Pricing Table**

| Period                       | 2025 | 2030 | 2035 | 2040 | 2045 | 2050 |
|------------------------------|------|------|------|------|------|------|
| Carbon Price (C$/tCO2)       | 125  | 170  | 170  | 170  | 170  | 170  |


**List of Technologies**

- `oil_extr_1` ... `oil_extr_6`
- `cement_CO2`
- `coal_extr`
- `gas_extr_1` ... `gas_extr_6`

The script calculates the OBPS for two scenarios: **Baseline** and **NetZero**.

### Baseline Scenario Based on Energy Future 2023

This section outlines the method for calculating the **Baseline Emission Intensity Reduction** using a five-year incremental model spanning from 2025 to 2055. The script retrieves CO2 emission values from the source dataset based on the year of activity. It then calculates the **Baseline Emission Intensity Reduction** for each interval, adhering to a policy that mandates a 20% reduction in emissions intensity compared to the average levels recorded in 2015. This reduction applies from 2020 to 2050. Should a facility surpass the established emissions intensity limit, it will be required to pay the backstop carbon price on the excess emissions.

### Net-Zero Scenario Based on Energy Future 2023

The **Canada Net-Zero Scenario** incorporates a 2% annual tightening of emissions intensity from 2023 to 2050. Under this scenario, an aggregate carbon cost are imposed on emissions that exceed the intensity limit. The **carbon cost for the Net-Zero scenario** is calculated using the payable emissions intensity under the Net-Zero framework, the carbon price (expressed in CAD per tonne of CO2), and a conversion rate of 0.73 for CAD to USD. Therefore, the final unit of measurement is in **USD/kWyr**.

## CO2_cc Relation Accuracy Analysis
This section includes in-progress steps and internal notes for collaboration, not part of the final documentation. The MESSAGEix-CA__baseline dataset from the common folder within the main GitLab repository is used as the base.

**Note**: Based on the MESSAGEix documentation, CO2_cc represents emissions of CO2 in central conversion and extraction. However, according to the provided guidelines, the CO2_cc relation is used to track CO2 emissions at the process level (or conversion) under a bottom-up analysis. Some Relation values for certain technologies vary over the years of activity, our calculations is based on the year_act 2020.

**Useful Formulas**
- To calculate Carbon Emissions from CO2 Emissions, use the formula:  
  **Carbon Emission = CO2 Emission × (12 / 44)**

- To determine Efficiency, apply the following equation:  
  **Efficiency = Output / Input = 1 / (Value from Input Dataset)**

- CO2_cc Relation:
  **CO2_cc × Efficiency = Emission Factor [tC/kWyr]**

Emission Factor Resource:
- [MESSAGEix Documentation](https://docs.messageix.org/projects/global/en/latest/emissions/message/index.html)
    - Example gas_ppl: CO2_cc=1.205 , Input Value (commodity: gas, Secondary)=2.5 GWa , Efficiency=0.4 , EF_Cal= 0.482 , EF_IPCC=0.482.
    -Example ref_lol: CO2_cc=0.0463 , Input Value (commodity: crudeoil, secondary)=1.078, Efficiency=0.927 , **EF_Cal=0.043 , EF_IPCC= 0.631**

| Fuel             | Emission factor [tC/kWyr] |
|------------------|--------------------------|
| Hard coal        | 0.814                    |
| Lignite          | 0.870                    |
| Crude oil        | 0.631                    |
| Light fuel oil   | 0.631                    |
| Heavy fuel oil   | 0.665                    |
| Methanol         | 0.549                    |
| Natural gas      | 0.482                    |
| Solid biomass    | 0.942                    |



