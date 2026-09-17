"""Every path the project uses, resolved from this file's own location.

Scripts live at varying depths under src/, so each one walking up its own
parents to find the repo root breaks the moment a file moves. Resolving it
once here means moving a script between folders costs nothing - which is
exactly what happened when the two tracks were merged into one project, and
this file absorbed both of their path modules.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATASETS = os.path.join(ROOT, "datasets")
RAW = os.path.join(DATASETS, "raw")
PROCESSED = os.path.join(DATASETS, "processed")
OUTPUTS = os.path.join(ROOT, "outputs")
SUBMISSION = os.path.join(ROOT, "submission")

# --- raw downloads, rebuilt from source by src/fetch ------------------------
EMIS_RAW = os.path.join(RAW, "emis_masterlists")
NSC_RAW = os.path.join(RAW, "nsc_reports")

# --- built tables, committed ------------------------------------------------
# school_year_panel   every school of every type, 2007-2025, as published
# clean_panel         the same after cleaning, restricted to matric-capable
# model_frame         clean_panel plus features and the target
# nsc_results         matric results extracted from the exam report PDFs
SCHOOL_PANEL = os.path.join(PROCESSED, "school_year_panel.csv.gz")
CLEAN_PANEL = os.path.join(PROCESSED, "clean_panel.csv.gz")
MODEL_FRAME = os.path.join(PROCESSED, "model_frame.csv.gz")
NSC_TABLE = os.path.join(PROCESSED, "nsc_results.csv")

# The pipeline's own name for the panel it starts from.
RAW_PANEL = SCHOOL_PANEL


def ensure(path):
    """Create a directory and return it, so callers can inline the call."""
    os.makedirs(path, exist_ok=True)
    return path


def out(name):
    """A path inside outputs/, creating the directory if it does not exist."""
    os.makedirs(OUTPUTS, exist_ok=True)
    return os.path.join(OUTPUTS, name)
