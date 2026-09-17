"""Every path the project uses, resolved from this file's own location.

Scripts live at varying depths under src/, so each one walking up its own
parents to find the repo root breaks the moment a file moves. Resolving it
once here means moving a script between folders costs nothing.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATASETS = os.path.join(ROOT, "datasets")
RAW = os.path.join(DATASETS, "raw")
PROCESSED = os.path.join(DATASETS, "processed")
OUTPUTS = os.path.join(ROOT, "outputs")

EMIS_RAW = os.path.join(RAW, "emis_masterlists")
NSC_RAW = os.path.join(RAW, "nsc_reports")

SCHOOL_PANEL = os.path.join(PROCESSED, "school_year_panel.csv.gz")
MODEL_TABLE = os.path.join(PROCESSED, "model_table.csv")
NSC_TABLE = os.path.join(PROCESSED, "nsc_results.csv")


def ensure(path):
    """Create a directory and return it, so callers can inline the call."""
    os.makedirs(path, exist_ok=True)
    return path
