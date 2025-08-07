# Specific Technoloigical Parameter Additions Sources

New technologies added to be MESSAGEix-Canada have been parameterized in the model utilizing the following sources:

Auto Thermal Reforming:

| **Data Type**                       | **Sheet Name(s)**                                                                                                                     | **Source**                                                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Costs**                           | `inv_cost`, `fix_cost`, `var_cost`                                                                                                    | Costs are based on difference in costs from extisting steam methane reforming technology as per http://dx.doi.org/10.1016/j.enconman.2022.115245|
| **Lifetime**                | `technical_lifetime`, 'construction_time'                                                                                                                     | Lifetime is based on https://www.nrel.gov/hydrogen/assets/docs/current-central-authothermal-reforming-of-natural-gas-with-co2-sequestration-version-aug22.xlsm                                                                       |
| **Emission Intensity**                  | `relation_activity'                                           | Emission intensity pulled from https://doi.org/10.1016/j.enconman.2022.115245                                               |
| **Energy Flows**              | `input`, `output`                                                                                                | |
| **Capacity Factor**            | `capacity_factor' | Value pulled from https://www.nrel.gov/hydrogen/assets/docs/current-central-authothermal-reforming-of-natural-gas-with-co2-sequestration-version-aug22.xlsm                                                                                                                                         |

---