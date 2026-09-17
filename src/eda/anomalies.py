"""Automated detection of discrepancies and anomalies in published school data.

This is the part of the project that answers the challenge directly. Every
defect below was found in South Africa's own published education data, and not
one of them raises an error. The files open, the row counts look reasonable,
the totals look plausible. A model trained on them learns something untrue and
reports it confidently.

That is what makes this class of fault worth automating. A crash gets noticed
within the hour. A province that silently becomes two, or a year that quietly
loses 1.4 million learners, survives all the way to a published finding.

Seven detectors, each returning what it found and how many schools it affects:

    collapsing_totals       a year where the national total breaks trend
    unstable_categories     the same fact spelled many ways
    label_churn             a school whose type changes and changes back
    impossible_values       values that are well formed and cannot be true
    coverage_gaps           a province that stops existing for a year
    identifier_breaks       schools that vanish and return
    duplicate_records       the same school twice in one year

Each returns a DataFrame. severity is HIGH where the defect would change a
model's answer, MEDIUM where it would distort a subgroup, LOW where it is
cosmetic but worth recording.
"""
import numpy as np
import pandas as pd

# A year-on-year change in national enrolment beyond this is not demography.
# South Africa's real annual movement is well under 3%.
TOTAL_SHIFT_TOLERANCE = 0.05

# Fields that should hold a small fixed set of values. Anything far beyond the
# expected count is spelling drift, not variety.
EXPECTED_VALUES = {
    "province": 9, "phase": 6, "quintile": 5,
    "nofee": 2, "urbanrural": 4, "status": 3, "sector": 2,
}

# South Africa spans roughly 22 to 35 degrees south, 16 to 33 east.
LAT_RANGE, LON_RANGE = (-35.0, -22.0), (16.0, 33.5)

COLUMNS = ["detector", "severity", "finding", "schools_affected", "detail"]


def _numeric(series):
    return pd.to_numeric(series, errors="coerce")


def _row(detector, severity, finding, schools, detail=""):
    return {"detector": detector, "severity": severity, "finding": finding,
            "schools_affected": int(schools), "detail": detail}


def collapsing_totals(panel):
    """A year where the national total breaks trend and then recovers.

    The 2017 masterlist reports 1.44 million fewer learners than 2016, and
    2018 reports 1.31 million more than 2017. No country loses eleven percent
    of its learners in a year and gets them back the next. It is a publication
    fault, and any target built on enrolment change would read it as thousands
    of schools collapsing at once.
    """
    frame = panel.copy()
    frame["year"] = _numeric(frame["year"])
    frame["learners"] = _numeric(frame["learners"])
    frame = frame.dropna(subset=["year", "learners"])

    totals = frame.groupby("year")["learners"].agg(["sum", "count"]).sort_index()
    totals["shift"] = totals["sum"].pct_change()

    found = []
    for year, row in totals.iterrows():
        if pd.isna(row["shift"]) or abs(row["shift"]) <= TOTAL_SHIFT_TOLERANCE:
            continue
        found.append(_row(
            "collapsing_totals", "HIGH",
            f"National enrolment moves {row['shift']:+.1%} in {int(year)}",
            row["count"],
            f"{row['sum']/1e6:.2f}M learners reported, against "
            f"{totals['sum'].shift(1).loc[year]/1e6:.2f}M the year before"))
    return pd.DataFrame(found, columns=COLUMNS)


def unstable_categories(panel):
    """The same fact published under many spellings.

    Left alone, a model reads "3" and "Q3" as unrelated funding bands and
    halves the signal from the strongest variable available. Province is the
    worst case: two provinces published under two codes each turn a country of
    nine into a dataset of eleven.
    """
    found = []
    for column, expected in EXPECTED_VALUES.items():
        if column not in panel.columns:
            continue
        values = panel[column].astype("string").str.strip()
        present = values[values.notna() & (values != "")]
        distinct = present.nunique()
        if distinct <= expected:
            continue
        severity = "HIGH" if distinct > expected * 2 else "MEDIUM"
        examples = ", ".join(map(repr, present.value_counts().index[:6]))
        found.append(_row(
            "unstable_categories", severity,
            f"'{column}' holds {distinct} distinct values where {expected} are possible",
            present.shape[0], f"most common: {examples}"))
    return pd.DataFrame(found, columns=COLUMNS)


def label_churn(panel, column="phase"):
    """A school whose type changes between years, and often changes back.

    Schools labelled combined one year and primary a few years later are a
    real population, and taking the label at face value admits schools with no
    matric class into a study about matric.
    """
    frame = panel[["emis", "year", column]].copy()
    frame["year"] = _numeric(frame["year"])
    frame = frame.dropna()

    changes = frame.groupby("emis")[column].nunique()
    churned = changes[changes > 1]
    if churned.empty:
        return pd.DataFrame([], columns=COLUMNS)

    severity = "HIGH" if len(churned) > 500 else "MEDIUM"
    return pd.DataFrame([_row(
        "label_churn", severity,
        f"{len(churned):,} schools change their '{column}' between years",
        len(churned),
        "a school that is combined in one year and primary in another cannot "
        "be filtered on this field alone")], columns=COLUMNS)


def impossible_values(panel):
    """Values that pass every type check and cannot be true.

    Latitude zero is a valid number and a point in the Atlantic Ocean, roughly
    2,000km off the coast. It survives every completeness report, and any
    distance measure built on it is wrong.
    """
    found = []

    if "lat" in panel.columns:
        lat, lon = _numeric(panel["lat"]), _numeric(panel["lon"])
        at_zero = int(((lat == 0) | (lon == 0)).sum())
        if at_zero:
            found.append(_row(
                "impossible_values", "HIGH",
                f"{at_zero:,} records placed at latitude or longitude zero",
                at_zero, "the Atlantic Ocean, not South Africa"))

        outside = int((lat.notna() & (lat != 0)
                       & ~lat.between(*LAT_RANGE)).sum())
        if outside:
            found.append(_row(
                "impossible_values", "MEDIUM",
                f"{outside:,} records outside South Africa's latitude range",
                outside, f"expected {LAT_RANGE[0]} to {LAT_RANGE[1]}"))

    if "learners" in panel.columns:
        learners = _numeric(panel["learners"])
        empty = int((learners.isna() | (learners <= 0)).sum())
        if empty:
            found.append(_row("impossible_values", "MEDIUM",
                              f"{empty:,} records with no usable learner count",
                              empty, "cannot contribute to any rate"))

    if {"learners", "educators"}.issubset(panel.columns):
        ratio = _numeric(panel["learners"]) / _numeric(panel["educators"])
        extreme = int((ratio > 100).sum())
        if extreme:
            found.append(_row("impossible_values", "MEDIUM",
                              f"{extreme:,} records with over 100 learners per educator",
                              extreme, "either a staffing crisis or a reporting fault"))
    return pd.DataFrame(found, columns=COLUMNS)


def coverage_gaps(panel):
    """A province that stops existing for a year.

    Northern Cape has no 2025 data because a Word template was published into
    that slot instead of a spreadsheet. Unhandled, a model reads it as a
    province whose schools all closed.
    """
    frame = panel.copy()
    frame["year"] = _numeric(frame["year"])
    frame = frame.dropna(subset=["year", "province"])

    grid = frame.pivot_table(index="province", columns="year",
                             values="emis", aggfunc="count").fillna(0)
    typical = grid.replace(0, np.nan).median(axis=1)

    found = []
    for province in grid.index:
        for year in grid.columns:
            count = grid.loc[province, year]
            if count == 0 or count < typical[province] * 0.5:
                found.append(_row(
                    "coverage_gaps", "HIGH",
                    f"{province} reports {int(count):,} schools in {int(year)}",
                    int(typical[province]),
                    f"typically {int(typical[province]):,} — the province appears "
                    "to vanish"))
    return pd.DataFrame(found, columns=COLUMNS)


def identifier_breaks(panel):
    """Schools that disappear from the record and return later.

    A gap in a school's history is usually renumbering rather than closure. Any
    trend measured across the gap is wrong, because the school did not actually
    shrink to nothing and grow back.
    """
    frame = panel[["emis", "year"]].copy()
    frame["year"] = _numeric(frame["year"])
    frame = frame.dropna().drop_duplicates()

    span = frame.groupby("emis")["year"].agg(["min", "max", "count"])
    span["expected"] = span["max"] - span["min"] + 1
    broken = span[span["count"] < span["expected"] - 1]
    if broken.empty:
        return pd.DataFrame([], columns=COLUMNS)

    return pd.DataFrame([_row(
        "identifier_breaks", "MEDIUM",
        f"{len(broken):,} schools have gaps in their year history",
        len(broken),
        "present, absent, then present again — usually renumbering, not closure"
    )], columns=COLUMNS)


def duplicate_records(panel):
    """The same school reported twice in one year."""
    counts = panel.groupby(["emis", "year"]).size()
    repeated = counts[counts > 1]
    if repeated.empty:
        return pd.DataFrame([], columns=COLUMNS)
    return pd.DataFrame([_row(
        "duplicate_records", "HIGH",
        f"{len(repeated):,} school-years appear more than once",
        repeated.index.get_level_values(0).nunique(),
        "double-counts any national total built from these rows")],
        columns=COLUMNS)


DETECTORS = (collapsing_totals, unstable_categories, label_churn,
             impossible_values, coverage_gaps, identifier_breaks,
             duplicate_records)


def scan(panel):
    """Run every detector and return one table of findings, worst first."""
    results = []
    for detector in DETECTORS:
        try:
            found = detector(panel)
        except Exception as exc:                 # a detector must never stop a scan
            found = pd.DataFrame([_row(detector.__name__, "LOW",
                                       f"detector failed: {type(exc).__name__}", 0)],
                                 columns=COLUMNS)
        if not found.empty:
            results.append(found)

    if not results:
        return pd.DataFrame([], columns=COLUMNS)

    table = pd.concat(results, ignore_index=True)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    table["_rank"] = table["severity"].map(order)
    return (table.sort_values(["_rank", "schools_affected"], ascending=[True, False])
            .drop(columns="_rank").reset_index(drop=True))


def summary(findings):
    """Headline counts for a slide or a dashboard tile."""
    return {
        "total_findings": len(findings),
        "high": int((findings["severity"] == "HIGH").sum()),
        "medium": int((findings["severity"] == "MEDIUM").sum()),
        "low": int((findings["severity"] == "LOW").sum()),
        "detectors_triggered": int(findings["detector"].nunique()),
    }
