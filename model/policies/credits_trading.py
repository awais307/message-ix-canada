scenario.check_out()

# Retrieve sscenarioario regions
regs = [n for n in scenario.set("node") if n not in ["World", "Canada"]]

# Retrieve sscenarioario modeling-horizon
years = [2025, 2030, 2035, 2040, 2045, 2050, 2060]

# Add dummy level and commodity
commodity = "credits"
level = "trade"
scenario.add_set("commodity", commodity)
scenario.add_set("level", level)

trade_cost = True
# Add new technologies
tecs = ["credits_buy", "credits_sell"]
for tec in tecs:
    scenario.add_set("technology", tec)

    if tec == "credits_buy":
        tce_coeff = -1
        eff_coeff = 1
        paramater = "input"
    else:
        tce_coeff = 1
        eff_coeff = 1
        paramater = "output"

    # Retrieve duration period length
    tlf = scenario.par("duration_period", filters={"year": years}).value.tolist()

    # Add technical lifetime
    for reg in regs:
        par = pd.DataFrame(
            {
                "node_loc": reg,
                "year_vtg": years,
                "technology": tec,
                "unit": "-",
                "value": tlf,
            }
        )
        scenario.add_par("technical_lifetime", par)

        if trade_cost:
            par = pd.DataFrame(
                {
                    "node_loc": reg,
                    "year_vtg": years,
                    "year_act": years,
                    "mode": "M1",
                    "technology": tec,
                    "time": "year",
                    "unit": "???",
                    "value": 40,
                }
            )
            scenario.add_par("var_cost", par)

        # Add emission_factor
        par = pd.DataFrame(
            {
                "node_loc": reg,
                "technology": tec,
                "year_vtg": years,
                "year_act": years,
                "mode": "M1",
                "emission": "TCE",
                "unit": "tC",
                "value": tce_coeff,
            }
        )
        scenario.add_par("emission_factor", par)

        # Add input/output
        if paramater == "input":
            par = pd.DataFrame(
                {
                    "node_loc": reg,
                    "node_origin": "Canada",
                    "level": level,
                    "commodity": commodity,
                    "year_vtg": years,
                    "year_act": years,
                    "time": "year",
                    "time_origin": "year",
                    "technology": tec,
                    "value": eff_coeff,
                    "mode": "M1",
                    "unit": "tC",
                }
            )
            scenario.add_par(paramater, par)

        if paramater == "output":
            par = pd.DataFrame(
                {
                    "node_loc": reg,
                    "node_dest": "Canada",
                    "level": level,
                    "commodity": commodity,
                    "year_vtg": years,
                    "year_act": years,
                    "time": "year",
                    "time_dest": "year",
                    "technology": tec,
                    "value": eff_coeff,
                    "mode": "M1",
                    "unit": "tC",
                }
            )
            scenario.add_par(paramater, par)

scenario.commit("Added certificate trade parametrization")
