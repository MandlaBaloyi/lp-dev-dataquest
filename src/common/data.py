"""Loading the built tables, in one place.

Both the app and the pipeline load through these functions, so neither can
quietly read something the other does not.
"""
import pandas as pd

from src.common.paths import CLEAN_PANEL, MODEL_FRAME, NSC_TABLE, SCHOOL_PANEL

# Everything is read as text. The source mixes numbers and markers in the same
# column - learner counts alongside "99", quintiles as both 3 and Q3 - and
# letting pandas infer types silently coerces those to NaN before the cleaning
# rules ever see them.


def load_panel(path=SCHOOL_PANEL, nrows=None):
    """The full school-year panel, every school type, exactly as published."""
    return pd.read_csv(path, dtype="string", nrows=nrows, keep_default_na=False)


def load_clean_panel(path=CLEAN_PANEL, nrows=None):
    """The panel after cleaning, restricted to schools that can hold a matric class."""
    return pd.read_csv(path, nrows=nrows)


def load_model_frame(path=MODEL_FRAME, nrows=None):
    """The clean panel plus engineered features and the target."""
    return pd.read_csv(path, dtype={"emis": str}, nrows=nrows)


def load_nsc(path=NSC_TABLE, nrows=None):
    """Matric results, extracted from the exam report PDFs."""
    return pd.read_csv(path, dtype={"emis": str}, nrows=nrows)
