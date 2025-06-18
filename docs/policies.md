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


# Canada Electricity Regulation (CER) Implementation in MESSAGEix-Canada

## Overview

This documentation explains the integration of the **Canada Electricity Regulation (CER)** in the MESSAGEix-Canada energy system model. The CER policy enforces a direct emission intensity limit on electricity generation technologies and allows offset credit purchases to partially comply with the regulation. This implementation reflects the design principles of Canada's  **Clean Electricity Regulations** , as well as regional policy variants from provinces such as **British Columbia (BC)** and  **Alberta** .

## Objective

Ensure that electricity generation emissions remain within a specified emission intensity threshold (e.g., tCO₂/MWh), while enabling partial compliance through the use of  **carbon offset credits** .

---

## Methodology

### 1. Relation Setup

Two new relations are introduced:

* `cer_direct_emission_intensity` → Enforces the main emissions intensity constraint.
* `cer_offset_limit` → Limits the maximum share of emissions that can be offset using purchased credits.

### 2. Relation Construction

#### a. Emission Intensity Constraint

For each emitting technology:

* **+1** assigned to the emission flow technology (e.g., `CO2_TCE`)
* **-λ** assigned to the electricity-generating technology's output flow (e.g., `electr` at `secondary` level)

This defines a linear inequality:

```
(+1 * Emissions) - (λ * Electricity Output) <= 0
```

Example: If λ = 0.065 tCO₂/MWh, it is transformed to 0.5694 MtC/GWyr.

#### b. Offset Contribution Constraint

Offsets are included with **+1** values in the `cer_direct_emission_intensity` relation. Additionally, the `cer_offset_limit` relation limits the contribution of offset purchases:

```
Total Offsets <= 10% of total allowed emissions
```

This is applied by:

* **+1** for offset technologies
* **-0.1 * λ** for electricity-generating technologies

### 3. Bound Setup

Both relations are given a hard constraint by setting:

```yaml
relation_upper:
  value: 0
```

This ensures emissions must stay within the permissible limit, including the offset cap.

---

## Provincial Carbon Prices for Offsets

| Province         | CAD/tCO₂ (2025) | USD2010/tCO₂ |
| ---------------- | ---------------- | ------------- |
| Alberta          | 65               | 39.00         |
| British Columbia | 40               | 24.00         |
| Federal (Rest)   | 50               | 30.00         |

**Conversion Note:** 1 CAD2025 → 0.75 USD2025, then divided by 1.25 to convert to USD2010.

These are added via the `tax_emission` parameter.

## References

* [*Canada Clean Electricity Regulations*](https://www.canada.ca/en/services/environment/weather/climatechange/climate-plan/clean-electricity.html)
* Alberta TIER Regulation (Add Link)
* British Columbia Carbon Market (Add Link)

---

## Limitations

* **Vintaging not accounted** : The CER does not currently differentiate between newly built and existing plants based on their commissioning date.
* **Static Thresholds** : The emission limits are hardcoded per policy design but may require updating for future policy revisions.
* **Technology Classification** : Inclusion of partial CCS and hydrogen-based generation can be context-sensitive and may require modeler judgment.

---

## Conclusion

This implementation of the CER provides a structured and policy-aligned mechanism for regulating emissions from electricity generation, offering flexibility via offsets, and maintaining system integrity through capped compliance mechanisms. This feature allows MESSAGEix-Canada to simulate decarbonization pathways under federal and provincial constraints effectively.


# Investment Tax Credit (ITC)

## 1. Policy Overview

The **Federal Investment Tax Credit (ITC)** is a refundable tax credit available to corporations that make capital investments in eligible clean technologies in Canada. The ITC policy is implemented in MESSAGEix-Canada by applying technology-specific investment cost reductions, based on assumptions from the **Open Insight Assumptions Database**. These reductions are applied over the model's time horizon using predefined input files.

---

## 2. Technology Scopes Covered by ITC Policy

The ITC implementation currently covers **three main technology scopes**. The fourth scope (Clean Technology Manufacturing) is not yet included.

### 2.1 Carbon Capture, Utilization, and Storage (CCUS ITC)

- **Input Variable**: `Input|Policy|ITCs|CCUS`
- **Scope**:
  - Applies ITC percentage investment cost reductions to **all CCS technologies except Direct Air Capture (DAC)**. DAC technologies are not modelled in MESSAGEix-Canada; hence, only non-DAC CCS technologies are included.
- **ITC Reduction Values**:
  - **Original Horizon**: 50% (2022–2030), 25% (2031–2040)
  - **Extended Horizon**: 50% (2022–2030), 25% (2041–2060)

---

### 2.2 Clean Technology ITC

- **Input Variable**: `Input|Policy|ITCs|Clean Technology`
- **Scope**:
  - Applies investment cost reductions to technologies classified as clean technology under the ITC.

### Clean Technology List and Implementation Status:
| **Technology Code**                                             | **Description**                                                                                   | **ITC Policy Implementation Status**            |
|------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|--------------------------------------------------|
| `wind_cv1`, `wind_cv2`, `wind_cv3`, `wind_cv4`                   | Onshore wind with flexibility requirements and firm capacity contributions. Includes quadratic systems integration costs. | Implemented                                      |
| `wind_ppf`                                                       | Offshore wind power plant (capacity only)                                                         | Implemented                                      |
| `wind_ppl`                                                       | Onshore wind power plant (capacity only)                                                          | Implemented                                      |
| `solar_cv1`, `solar_cv2`, `solar_cv3`, `solar_cv4`               | Solar PV with quadratic system integration costs                                                  | Implemented                                      |
| `solar_i`                                                        | Solar thermal in the industry thermal sector                                                      | Implemented                                      |
| `solar_pv_ppl`                                                   | Solar photovoltaic power plant (no storage)                                                       | Implemented                                      |
| `solar_th_ppl`                                                   | Solar thermal power plant with storage                                                            | Implemented                                      |
| `hydro_hc`                                                       | High-cost hydro power plant                                                                       | Implemented                                      |
| `hydro_lc`                                                       | Low-cost hydro power plant                                                                        | Implemented                                      |
| `stor_ppl`                                                       | Generic electric storage system                                                                   | Implemented – Added After Revision               |
| `hp_el_i`                                                        | Electric heat pump in the industry thermal sector                                                 | Implemented – Added After Revision               |
| `hp_gas_i`                                                       | Natural gas heat pump in the industry thermal sector                                              | Implemented – Added After Revision               |
| `geo_hpl`                                                        | Geothermal heat plant                                                                             | Implemented – Added After Revision               |
| `geo_ppl`                                                        | Geothermal power plant                                                                            | Implemented – Added After Revision               |
| `solar_th_ppl__air`, `solar_th_ppl__cl_fresh`, `solar_th_ppl__ot_fresh`, `solar_th_ppl__ot_saline` |                             ---                                                                                                         | Listed but Not Implemented                       |


> **Legend – ITC Policy Implementation Status**

- **Implemented**:  
  Technology included in the Clean Technology ITC input file and successfully implemented in the model.

- **Implemented – Added After Revision**:  
  Technology not included in the initial Clean Technology ITC input file but added after a revision of model implementation scope and successfully implemented in the model.

- **Listed but Not Implemented**:  
  Technology included in the initial Clean Technology ITC input file file but not implemented due to missing required parameters (e.g., `inv_cost`) in the model.

---
### 2.3 Clean Hydrogen ITC

- **Input Variable:** `Input|Policy|ITCs|Clean Hydrogen`
- **Scope:**  
  - This scope applies ITC reductions to hydrogen production technologies. In the current version of the model, the ITC is applied **only to the technology `h2_elec` (hydrogen production via electrolysis)**.

The **Open Insight Assumptions Database** defines four ITC value levels based on the carbon intensity (CI) of the hydrogen production technology:

| **Carbon Intensity (CI) Range** | **ITC Reduction Value**       |
|----------------------------------|---------------------|
| CI < 0.75                        | 40 %       |
| 0.75 ≤ CI < 2.0                  | 25 %                |
| 2.0 ≤ CI < 4.0                   | 15 %              |
| CI ≥ 4.0                         | 0 or Not Eligible |

> **Note:** In this implementation, the model **uses the highest tier (CI < 0.75)** to determine the ITC reduction value applied to `h2_elec`. Users may modify the CI thresholds and associated ITC values in the input file to enable flexible scenario testing.

---

## 3. Limitations and Special Notes

### 3.1 DAC Technologies

- DAC is excluded since it is not modelled in the current version of MESSAGEix-Canada.
- `Input|Policy|ITCs|CCUS` applies only to non-DAC CCS technologies.

### 3.2 CO₂ Transport and Storage

- The eligible technology `co2_tr_dis`, which covers CO₂ transportation and disposal, does not have an associated investment cost (`inv_cost`) defined in the model. Therefore, the ITC cannot be applied to this technology.
- Investment costs related to **CO₂ capture** are incorporated within the corresponding power plant technologies.

### 3.3 Eligible Clean Technologies Without ITC Application
- The ITC cannot be applied to technologies that lack defined investment costs `inv_cost` or explicit representation in the model. These include:
  - `hp_el_rc` (electric heat pump in residential/commercial)
  - `hp_gas_rc` (natural gas heat pump in residential/commercial)
  - Small Modular Reactors (SMRs) are not modelled explicitly. Only `nuc_hc` and `nuc_lc` nuclear technologies exist; custom model modifications required for SMRs.

### 3.4 Carbon Sequestration Output Variable

- **Output** `Carbon Sequestration|CCS|Industrial`
represents the total CO₂ captured from industrial processes and stored geologically. This output is linked to industrial technologies that include carbon capture and storage. Since the ITC policy has already been applied to all CCS-related technologies, this output category is effectively covered under the CCS ITC policy.

---

## 4. Model Implementation and Setup

### 4.1 Core ITC Application Function

- The ITC policy is activated by setting the `investment_tax_credit` flag to `true` in the `ModelSetup_CA.yaml` file.
- The `Investment_tax_credit.py` script contains the function `add_investment_tax_credit()`. This function applies the ITC percentage deduction to the `inv_cost` parameter of eligible technologies for each model year.

**Calculation:**

```python
adjusted_inv_cost = inv_cost * (1 - (ITC_Value / 100))
```

### 4.2 ITC Input Files and Time Horizons

The ITC policy uses CSV input files that define the percentage investment cost reduction values by technology scope and year. Two versions of these input files exist:

- **Original Horizon Input File** (`assumptions_database_ITCs_OriginalHorizon.csv`):
  - Applies ITC values from **2022 to 2040** for CCUS.
  - Applies ITC values from **2023 to 2034** for Clean Hydrogen and Clean Technology.

- **Extended Horizon Input File** (`assumptions_database_ITCs_ExtendedHorizon.csv`):
  - Extends the ITC values beyond original time horizon up to **2060** following the original policy format.

Users select which input file to apply when configuring the `ModelSetup_CA.yaml` file.


