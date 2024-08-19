import pandas as pd
import numpy as np

def map_yv_ya_lt(
    periods: Tuple[int, ...], lt: int, ya: Optional[int] = None
) -> pd.DataFrame:
    """All meaningful combinations of (vintage year, active year) given periods.
    Parameters
    ----------
    labels : pandas.DataFrame
        Each column (dimension) corresponds to one in df. Each row represents one
        matched set of labels for those dimensions.
    lt : int, lifetime
    """
    if not ya:
        ya = periods[0]
        log.info(f"First active year set as {ya!r}")
    if not lt:
        raise ValueError("Add a fixed lifetime parameter 'lt'")
    # The following lines are the same as
    # message_ix.tests.test_feature_vintage_and_active_years._generate_yv_ya
    # - Create a mesh grid using numpy built-ins
    # - Take the upper-triangular portion (setting the rest to 0)
    # - Reshape
    data = np.triu(np.meshgrid(periods, periods, indexing="ij")).reshape((2, -1))
    # Filter only non-zero pairs
    df = pd.DataFrame(
        filter(sum, zip(data[0, :], data[1, :])),
        columns=["year_vtg", "year_act"],
        dtype=np.int64,
    )
    # Select values using the ya and lt parameters
    return df[(ya <= df.year_act) & (df.year_act - df.year_vtg <= lt)]
