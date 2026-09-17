"""Merging the two tracks: enrolment signals plus matric outcomes.

WHY MERGE AT ALL

The two tracks asked different questions of the same schools.

The independent track asked whether a school's enrolment would fall faster
than its province over the next two years, using the enrolment panel alone. It
reached 0.654 AUC on test - a working triage list.

The primary track asked whether fewer of a school's learners reach matric than
comparable schools, using matric results extracted from the exam report PDFs.
It reached 0.539, barely above chance, because whole-school enrolment is too
coarse a denominator to measure attrition cleanly.

The second question failed. The data gathered to answer it did not. Matric
results say something about a school that enrolment counts cannot: how many
learners actually reached the end, how many were pushed through without
meeting requirements, and whether that is getting worse. None of it is
derivable from a learner headcount.

So the merge keeps the independent track's target, which is answerable, and
adds the primary track's data as predictors. The question being tested is
narrow and worth asking: does knowing how a school's matric cohort behaved
tell you anything about whether that school is about to start shedding
learners?

THE TIMING RULE STILL HOLDS

The outcome is observed two years after the feature year. Every matric feature
here is built from year Y and earlier, never later, so nothing reaches forward
into the window it is predicting.
"""
import numpy as np
import pandas as pd

from src.common.paths import PROCESSED, ROOT
import os

MODEL_FRAME = os.path.join(ROOT, "independent", "data", "model_frame.csv.gz")
NSC_TABLE = os.path.join(PROCESSED, "nsc_results.csv")

# Built from matric results, which the enrolment panel cannot produce.
MATRIC_FEATURES = [
    "throughput", "throughput_chg1", "throughput_chg3", "throughput_vol",
    "progressed_share", "progressed_share_chg1",
    "wrote_chg1", "wrote_chg3", "pass_rate", "pass_rate_chg1",
    "matric_years_seen",
]


def matric_features(nsc, panel_sizes):
    """Per school per year, from that year backwards only.

    panel_sizes supplies enrolment so throughput can be expressed as a share
    of the school rather than a raw count, which is not comparable between a
    village school and a metro one.
    """
    frame = nsc.copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["wrote"] = pd.to_numeric(frame["wrote"], errors="coerce")
    frame["progressed"] = pd.to_numeric(frame["progressed"], errors="coerce")
    frame["pass_rate"] = pd.to_numeric(frame["pass_rate"], errors="coerce")
    frame = frame.dropna(subset=["emis", "year", "wrote"])
    frame = frame.sort_values(["emis", "year"])

    frame = frame.merge(panel_sizes, on=["emis", "year"], how="left")
    frame["throughput"] = frame["wrote"] / frame["learners"].replace(0, np.nan)

    # Share of the matric cohort advanced without meeting the requirements.
    # A school leaning on this is carrying learners it has not been able to
    # bring up to standard, which is a different thing from a low pass rate.
    frame["progressed_share"] = frame["progressed"] / frame["wrote"].replace(0, np.nan)

    by_school = frame.groupby("emis", sort=False)
    for column in ("throughput", "progressed_share", "wrote", "pass_rate"):
        for span in (1, 3):
            previous = by_school[column].shift(span)
            name = f"{column}_chg{span}"
            if name.startswith(("throughput", "wrote", "pass_rate")):
                frame[name] = (frame[column] - previous) / previous.replace(0, np.nan)
            else:
                frame[name] = frame[column] - previous

    frame["throughput_vol"] = by_school["throughput"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=2).std())
    frame["matric_years_seen"] = by_school.cumcount()

    keep = ["emis", "year"] + [c for c in MATRIC_FEATURES if c in frame.columns]
    return frame[keep].replace([np.inf, -np.inf], np.nan)


def build():
    """The independent track's frame, with matric predictors joined on."""
    frame = pd.read_csv(MODEL_FRAME, dtype={"emis": str})
    nsc = pd.read_csv(NSC_TABLE, dtype={"emis": str})

    sizes = frame[["emis", "year", "learners"]].drop_duplicates()
    extra = matric_features(nsc, sizes)

    merged = frame.merge(extra, on=["emis", "year"], how="left")
    merged["has_matric_data"] = merged["throughput"].notna().astype(int)
    return merged
