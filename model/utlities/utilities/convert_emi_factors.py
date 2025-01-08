class main(object):
    def __init__(self, scenario, verbose=False):
        self.scenario = scenario
        self.verbose = verbose

        # Retrieve all unused emission_factor
        df_emif = self.scenario.par("emission_factor")
        df_emif = df_emif[
            df_emif.emission.isin(
                [
                    e
                    for e in df_emif.emission.unique().tolist()
                    if e
                    not in [
                        "fresh_thermal_pollution",
                        "fresh_wastewater",
                        "saline_thermal_pollution",
                        "saline_wastewater",
                        "TCE",
                    ]
                ]
            )
        ]

        # Retrieve all unused type_emission
        df_emit = self.scenario.set("type_emission")
        df_emit = df_emit[~df_emit.isin(["TCE"])]

        # Retrieve all unused emission_scaling
        df_emis = self.scenario.par("emission_scaling")
        df_emis = df_emis[~df_emis["type_emission"].isin(["TCE"])]

        self.scenario.check_out()
        # Remove emission_factor
        self.scenario.remove_par("emission_factor", df_emif)
        if self.verbose:
            for emi in df_emif.emission.unique():
                print("Emission Factor: {} - removed".format(emi))

        # Remove emission_scaling
        self.scenario.remove_par("emission_scaling", df_emis)
        if self.verbose:
            for emi in df_emis.type_emission.unique():
                print("Emission scaling: {} - removed".format(emi))

        # Remove type_emission
        for t in df_emit.values.tolist():
            self.scenario.remove_set("type_emission", t)
            if self.verbose:
                print("Type Emission: {} - removed".format(t))
        self.scenario.commit("removed all emif")