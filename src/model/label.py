"""Defining what the model predicts.

The ideal measure is cohort survival: of the learners who started Grade 10 at a
school, how many reached matric. That needs per-grade enrolment, which is held
under separate permission. What we have is total enrolment per school per year
and matric candidates per school per year, so the measure is throughput:

    throughput(Y) = matric candidates in year Y / total enrolment in year Y-2

WHY THE TWO-YEAR LAG
Enrolment counts every grade, so for a stable school enrolment two years ago
and enrolment now are nearly the same and the lag looks pointless. It matters
precisely for the schools this project is about. A school that has been losing
learners has a smaller enrolment today, and dividing by today's figure would
flatter it - the denominator shrinks alongside the numerator and the loss
disappears. Measuring against what the school was before the cohort passed
through keeps that loss visible.

WHY THROUGHPUT IS THEN INDEXED
Raw throughput cannot be compared across school types. A secondary school
spans five grades and a combined school twelve, so an identical throughput
means very different things. Rather than assuming how enrolment divides across
grades - which is itself distorted by the dropout being measured - each school
is compared against the median for its own phase in its own year:

    survival_index = throughput / median throughput for that phase and year

A school at 1.0 is typical for its type that year. Below 1.0, fewer of its
learners are reaching matric than is normal for schools like it. Indexing by
year also absorbs national shifts, so a bad year for everyone does not register
as thousands of newly failing schools.

THE BINARY TARGET
The metrics this project reports - AUC, Gini, precision, recall - and weight of
evidence all require a binary outcome, so the index is thresholded:

    is_high_risk = 1 where survival_index falls in the worst fifth of schools
                     that year

The cut is taken from the observed distribution rather than set at a round
number, which makes it answerable: "the worst-performing fifth of schools in
the country" is a statement about policy. "Below 0.6" is a statement about
nothing.

WHAT THIS IS NOT
It is a throughput indicator, not a count of individual learners. It cannot
separate a school losing learners from a school whose intake is shrinking for
demographic reasons. Enrolment trend is carried alongside every score so a user
can tell which is happening, and the limitation is stated wherever the number
appears.
"""
import pandas as pd

ENROLMENT_LAG = 2
HIGH_RISK_QUANTILE = 0.20

# Below this, one learner moves the rate by several points and the measure is
# noise rather than signal.
MIN_ENROLMENT = 50
MIN_CANDIDATES = 10


def build(panel, nsc, lag=ENROLMENT_LAG, quantile=HIGH_RISK_QUANTILE):
    """One row per school-year with a throughput measure and a binary target.

    panel  school-year enrolment, requires emis, year, learners, phase
    nsc    matric results, requires emis, year, wrote
    """
    schools = panel.copy()
    schools["year"] = pd.to_numeric(schools["year"], errors="coerce")
    schools["learners"] = pd.to_numeric(schools["learners"], errors="coerce")
    schools = schools.dropna(subset=["emis", "year", "learners"])

    results = nsc.copy()
    results["year"] = pd.to_numeric(results["year"], errors="coerce")
    results["wrote"] = pd.to_numeric(results["wrote"], errors="coerce")
    results = results.dropna(subset=["emis", "year", "wrote"])

    # Match each matric year to the enrolment recorded `lag` years earlier.
    earlier = schools[["emis", "year", "learners", "phase"]].copy()
    earlier["year"] = earlier["year"] + lag
    earlier = earlier.rename(columns={"learners": "enrolment_before"})

    merged = results.merge(earlier, on=["emis", "year"], how="inner")

    merged = merged[(merged["enrolment_before"] >= MIN_ENROLMENT)
                    & (merged["wrote"] >= MIN_CANDIDATES)]
    if merged.empty:
        return merged.assign(throughput=[], survival_index=[], is_high_risk=[])

    merged["throughput"] = merged["wrote"] / merged["enrolment_before"]

    # Compare like with like: same phase, same year.
    typical = (merged.groupby(["phase", "year"])["throughput"]
               .transform("median"))
    merged["survival_index"] = merged["throughput"] / typical

    # Threshold within each year, so the target means the same thing in 2012
    # as in 2024 and a nationally bad year does not flood the positive class.
    cut = merged.groupby("year")["survival_index"].transform(
        lambda s: s.quantile(quantile))
    merged["is_high_risk"] = (merged["survival_index"] <= cut).astype(int)

    return merged.sort_values(["emis", "year"]).reset_index(drop=True)


def summarise(frame):
    """Distribution of the target, for checking it is sane before training."""
    total = len(frame)
    return {
        "rows": total,
        "schools": int(frame["emis"].nunique()),
        "years": f"{int(frame['year'].min())}-{int(frame['year'].max())}",
        "high_risk": int(frame["is_high_risk"].sum()),
        "high_risk_pct": round(100 * frame["is_high_risk"].mean(), 1),
        "throughput_median": round(float(frame["throughput"].median()), 3),
        "index_median": round(float(frame["survival_index"].median()), 3),
    }
