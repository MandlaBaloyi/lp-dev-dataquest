"""Data quality profiling for the raw school panel.

Answers the questions you have to answer before trusting anything downstream:
what is missing, what is inconsistently spelled, and what is impossible.

The distinction that matters here is between missing and dirty. A blank cell is
missing and obvious. A column holding both "3" and "Q3" is dirty and invisible -
nothing errors, the data looks complete, and a model reads two categories where
there is one. Dirty is the dangerous kind, so it gets its own report.
"""
import pandas as pd

from src.features import clean

# Columns whose values should come from a small fixed set. Anything with far
# more distinct values than expected is showing spelling drift, not variety.
CATEGORICAL_EXPECTATIONS = {
    "phase": 6,
    "quintile": 5,
    "nofee": 2,
    "urbanrural": 4,
    "status": 2,
    "sector": 2,
    "province": 9,
}


def completeness(frame):
    """Per column: how much is present, how much is missing, how varied it is."""
    total = len(frame)
    rows = []
    for column in frame.columns:
        series = frame[column].astype("string").str.strip()
        blank = series.isna() | series.eq("")
        filled = total - int(blank.sum())
        rows.append({
            "column": column,
            "filled": filled,
            "filled_pct": round(100 * filled / total, 1) if total else 0.0,
            "missing": int(blank.sum()),
            "distinct": int(series[~blank].nunique()),
        })
    return pd.DataFrame(rows).sort_values("filled_pct")


def dirty_categoricals(frame):
    """Columns carrying more distinct values than the field can legitimately hold.

    The gap between actual and expected is the number of spellings that need
    mapping before the column is usable.
    """
    rows = []
    for column, expected in CATEGORICAL_EXPECTATIONS.items():
        if column not in frame.columns:
            continue
        actual = int(frame[column].astype("string").str.strip().nunique())
        rows.append({
            "column": column,
            "distinct_raw": actual,
            "expected": expected,
            "excess": max(0, actual - expected),
            "needs_cleaning": actual > expected,
        })
    return pd.DataFrame(rows).sort_values("excess", ascending=False)


def value_counts(frame, column):
    """Every distinct value in a column, with the cleaned value beside it.

    This is the table that makes a cleaning rule auditable: you can see exactly
    which raw spellings collapse into which cleaned category, and how many rows
    each decision moves.
    """
    counts = (frame[column].astype("string").fillna("")
              .value_counts(dropna=False).reset_index())
    counts.columns = ["raw_value", "rows"]
    cleaner = clean.CLEANERS.get(column)
    if cleaner:
        counts["cleaned_to"] = counts["raw_value"].map(cleaner)
    return counts


def impossible_values(frame):
    """Values that are well-formed but cannot be true.

    These pass every type check and every missing-value report. Latitude 0 is a
    real number in a numeric column; it is also a point in the Atlantic Ocean.
    """
    findings = []

    if "lat" in frame.columns:
        lat = pd.to_numeric(frame["lat"], errors="coerce")
        findings.append({
            "check": "latitude is 0 (Atlantic Ocean, not a school)",
            "rows": int((lat == 0).sum()),
        })
        outside = lat.notna() & ~lat.between(-35, -22) & (lat != 0)
        findings.append({
            "check": "latitude outside South Africa (-35 to -22)",
            "rows": int(outside.sum()),
        })

    if "learners" in frame.columns:
        learners = pd.to_numeric(frame["learners"], errors="coerce")
        findings.append({"check": "learner count missing or zero",
                         "rows": int((learners.isna() | (learners <= 0)).sum())})
        findings.append({"check": "learner count above 5,000 (implausible)",
                         "rows": int((learners > 5000).sum())})

    if {"learners", "educators"}.issubset(frame.columns):
        learners = pd.to_numeric(frame["learners"], errors="coerce")
        educators = pd.to_numeric(frame["educators"], errors="coerce")
        ratio = learners / educators
        findings.append({"check": "more than 100 learners per educator",
                         "rows": int((ratio > 100).sum())})

    if "school" in frame.columns:
        name = frame["school"].astype("string").str.upper()
        findings.append({"check": "school name is UNKNOWN",
                         "rows": int(name.str.contains("UNKNOWN", na=False).sum())})

    return pd.DataFrame(findings)


def coverage_matrix(frame, index="year", columns="province"):
    """Row counts by year and province - exposes a province missing a year.

    Northern Cape has no 2025 row because DBE published a Word template into
    that slot. A gap like that is invisible in a total but obvious in a grid.
    """
    return (frame.pivot_table(index=index, columns=columns,
                              values=frame.columns[0], aggfunc="count")
            .fillna(0).astype(int))
