"""Loading the panel, in one place.

Both the app and the pipeline load the same file through this function, so
neither can quietly read something the other does not.
"""
import pandas as pd

from src.common.paths import SCHOOL_PANEL, MODEL_TABLE

# Everything is read as text. The source mixes numbers and markers in the same
# column - learner counts alongside "99", quintiles as both 3 and Q3 - and
# letting pandas infer types silently coerces those to NaN before the cleaning
# rules ever see them.
def load_panel(path=SCHOOL_PANEL, nrows=None):
    """The full school-year panel, all school types, as published."""
    return pd.read_csv(path, dtype="string", nrows=nrows, keep_default_na=False)


def load_model_table(path=MODEL_TABLE, nrows=None):
    """The reduced table: secondary and combined schools only."""
    return pd.read_csv(path, dtype="string", nrows=nrows, keep_default_na=False)
