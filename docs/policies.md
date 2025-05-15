# Policies

## *OBPS*

Canada's Output-Based Pricing System (OBPS) is a federal policy aimed at reducing greenhouse gas emissions from large industrial facilities while maintaining their competitiveness. Instead of paying a blanket carbon tax, facilities under the OBPS are assigned emissions-intensity performance standards based on their production output. Facilities emitting below their assigned limit earn surplus credits, which can be sold or saved for future use. Those exceeding the limit must compensate by purchasing credits or paying a fee aligned with the federal carbon price.

More information on the OBPS policy can be found at https://www.canada.ca/en/environment-climate-change/services/climate-change/pricing-pollution-how-it-will-work/output-based-pricing-system.html

***Model Implementation***

In Messageix-Canada, the OBPS framework is incorporated by first developing a payable emission intensity. OBPS emission standards are defined by selecting a technology to map to a standard, then utilizing that technologies emiision intensity and multiplying by a defined reduction as outlined in the OBPS policy.

![](include/Standard_Diagram.png)

A list of a MESSAGEix technologies mapped to create standards can be found below:

| **Standard**                                      | **Standard Technology** | **Description**                               |
| ------------------------------------------------------- | ----------------------------- | --------------------------------------------------- |
| **Mining & Ore Processing, Coal, Sub-bituminous** | coal_extr                     | Coal extraction                                     |
| **Electricity Generation, Solid Fuels**           | coal_ppl                      | Coal power plant                                    |
| **Oil & Gas, Natural Gas, Pipieline Quality**     | gas_extr_3                    | Natural Gas extraction from ...                     |
| **Final Energy, Industry, Feedstock**             | gas_fs                        | Natural Gas as an industry feedstock                |
| **Final Energy, Industry**                        | gas_i                         | Natural Gas use in industrial applications          |
| **Electricity Generation, Gaseous Fuels, New**    | gas_ppl                       | Natural Gas power plant                             |
| **Oil & Gas, Natual Gas, Transmission**           | gas_t_d                       | Gas transmission and distribution                   |
| **Oil & Gas, Hydrogen**                           | h2_smr                        | Hydrogen production through steam-methane reforming |
| **Oil & Gas, Natural Gas, Liquids**               | LNG_regas                     | Gasification of liquid natural gas                  |
| **Electricity Generation, Liquid Fuels**          | loil_ppl                      | Light oil power plant                               |
| **Chemical, Petrochemicals, High Value**          | meth_ng                       | Methanol production from natural gas                |
| **Oil & Gas, Crude Oil ,Heavys**                  | oil_extr_3                    | Oil extraction from ...                             |

The difference between the OBPS emission standard and a technologies emission intensity is the payable emission intensity. For years after 2023, the OBPS standard is decreased by a legislated and mapped tightening rate to further tax applicable tachnologies in the model, as the policy was designed. For model years past 2035, it is assumed that the policy remains active and tightening rates continue to grow following the same trends as before 2035. However, as with many other aspects of the model, users have the ability to vary the tightening rates to explore future scenarios. Where applicable, provinces that have specified their own standards and tightening rates have been mapped and applied. This includes Alberta, British Columbia, New Brunswick, Nova Scotia, Newfoundland and Labrador, Ontario, and Saskatchewan.

![](include/Payable_Emission_Intensity_Diagram.png)

This payable emission intensity is then multiplied by the federal carbon price to createa carbon cost that is then applied to the mapped MESSAGEix-Canada technologies for each respective temporal period. Like the OBPS tightening rates, it is assumed that federal carbon price will continue to grow post 2035 at the same specified rate as before 2035, however this can be varried by users should one desire.

![](include/Carbon_Cost_Diagram.png)

As MESSAGEix-Canada is unable to depict revenue streams, credits must be depicted a different way. When OBPS mapped technologies have a lower emission intensity then the OBPS emission standards a negative “receivable emission intensity” can be defined. The amount of “payable” and “receivable” emission intensities can then be tracked. Through an iterative process, the credit price was varied until supply and demand of credits roughly matched in the model results.

# Canada Electricity Regulation (CER)

## Overview

This documentation describes the implementation of the **Canada Electricity Regulation** **(CER)** policy in the MESSAGEix-Canada model. The policy enforces direct emission intensity limits on electricity generation technologies, while allowing offset purchases as a compliance mechanism. This feature is designed to reflect Canada's **Clean Electricity Regulations** framework and provincial climate policies such as those in **British Columbia (BC)** and  **Alberta** .

## Objective

To ensure that electricity generation technologies meet a  **maximum allowed emission intensity threshold** , while optionally purchasing offset credits if the emissions exceed the allowed limit.

---

## Methodology

### Relation Setup

A new relation `cer_direct_emission_intensity` is introduced in the model to enforce the CER constraint.

#### Step 1: Adding Technologies

We identify **electricity generation technologies** from the model that emit carbon dioxide, using the following logic:

* **Include** fossil and bioenergy-based generation technologies.
* **Exclude** renewables (e.g., wind, solar), zero-emission imports, and negative-emission technologies unless they are partial CCS.

#### Step 2: Constructing the Relation

The CER relation is constructed by assigning:

* **+1** to the emitting technology's **CO2 emission activity** (e.g., `CO2_TCE` or `CO2_emission` technology).
* **-λ** to the technology's **electricity output** (e.g., `electr` at `secondary` level), where λ is the emission intensity threshold.

This structure ensures that a technology can only operate within the allowed emission limits:

```
(+1 × Emissions) - (λ × Electricity Output) <= 0
```

> Example: If λ = 0.065 tCO2/MWh, it is transformed to 0.5694 MtC/GWyr.

#### Step 3: Offsets

Technologies can purchase offsets to compensate for excess emissions:

* Offset technologies (e.g., `credits_purchase`) are added to the relation with a **+1** value, contributing positively.
* These are assigned a `tax_emission` cost based on provincial/federal carbon market values.

#### Step 4: Emission Constraint Application

The upper bound of the relation is set to 0, making it a  **hard constraint** :

```yaml
relation_upper:
  relation: cer_direct_emission_intensity
  node_rel: <Province>
  year_rel: <Year>
  value: 0
```

---

## Provincial Carbon Prices for Offsets

| Province         | CAD/tCO2 (2025) | USD2010/tCO2 |
| ---------------- | --------------- | ------------ |
| Alberta          | 65              | 39.00        |
| British Columbia | 40              | 24.00        |
| Federal (Rest)   | 50              | 30.00        |

> Conversion: 1 CAD2025 = 0.75 USD2025, then divided by 1.25 to convert to USD2010.

Carbon prices are applied using the `tax_emission` parameter.

---

## Sample Implementation Snippets

### Emission Relation Example

```csv
relation,node_rel,year_rel,node_loc,technology,year_act,mode,value,unit
cer_direct_emission_intensity,Alberta,2030,Alberta,CO2_TCE,2030,M1,1,-
cer_direct_emission_intensity,Alberta,2030,Alberta,bio_istig,2030,M1,-0.5694,-
```

### Offset Example

```csv
relation,node_rel,year_rel,node_loc,technology,year_act,mode,value,unit
cer_direct_emission_intensity,Alberta,2030,Alberta,credits_purchase,2030,M1,1,-
```

### Tax Emission for Offsets

```csv
tax_emission,node,year,technology,mode,emission,value,unit
Alberta,2030,credits_purchase,M1,TCE,39.0,USD/tC
```

---

## References

* [*Clean Electricity Regulations*](https://www.canada.ca/en/services/environment/weather/climatechange/climate-plan/clean-electricity.html)
* British Columbia Carbon Pricing (TODO: Add Link)
* Alberta TIER Regulation (TODO: Add Link)

---

## Notes and Limitations

* The emission factor values are not modified during this implementation. Existing `emission factors`  are used.
* Renewable technologies (wind, hydro, solar) are excluded from the CER relation.
* This relation is enforced from 2025 onwards.
