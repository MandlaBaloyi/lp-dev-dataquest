"""Paths for the independent track, resolved from this file's location."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK = os.path.dirname(HERE)
ROOT = os.path.dirname(TRACK)

RAW_PANEL = os.path.join(ROOT, "datasets", "processed", "school_year_panel.csv.gz")

DATA = os.path.join(TRACK, "data")
OUTPUTS = os.path.join(TRACK, "outputs")

CLEAN_PANEL = os.path.join(DATA, "clean_panel.csv.gz")
MODEL_FRAME = os.path.join(DATA, "model_frame.csv.gz")


def out(name):
    os.makedirs(OUTPUTS, exist_ok=True)
    return os.path.join(OUTPUTS, name)
