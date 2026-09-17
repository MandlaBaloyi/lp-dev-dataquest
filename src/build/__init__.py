"""Stage 2 - turn raw downloads into tables worth analysing.

    school_panel.py   folds 234 spreadsheets into one row per school per year
    model_table.py    reduces that panel to the population being modelled

school_panel.py carries most of the difficulty, because the source is
inconsistent in ways that raise no error. Column names drift between years,
the same province is published under two different codes, and one file has its
key column header truncated to a single letter. Each of those silently removed
data while leaving a panel that looked healthy, so this module matches headers
case-insensitively, normalises province codes, and recovers a mislabelled
column by inspecting its values rather than trusting its name.

model_table.py answers a narrower question: which rows belong in the model at
all. Only schools that can hold a Grade 10-12 cohort qualify. A primary school
has no matric class, so it cannot contribute an observation about matric
attrition.
"""
