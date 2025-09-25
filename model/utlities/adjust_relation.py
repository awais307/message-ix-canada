def update_relation(ctx, nodes, relation, technology, value, years="all"):
    """
    Replace max or min shares in "relation_activity" by a new value.

    Parameters
    ----------
    nodes : list of str or 'all'
        Nodes to apply the change in a relation.
    relation : str
        Relation name.
    technology : str
        Technology to which the value is being updated.
    value : float
        New coefficient for the technology in the relation.
    years : list or "all", optional
        Years to apply the change. Default is "all".
    """
    scenario = ctx.source_scenario["scenario"]
    if nodes == "all":
        nodes = scenario.set("node").tolist()[2:]

    with scenario.transact("Replace values in a relation"):
        df = scenario.par(
            "relation_activity",
            {"relation": relation, "technology": technology, "node_loc": nodes},
        )

        # Filter by specific years if provided
        if years != "all":
            df = df.loc[df["year_act"].isin(years)].copy()

        if not df.empty:
            df["value"] = value
            scenario.add_par("relation_activity", df)
