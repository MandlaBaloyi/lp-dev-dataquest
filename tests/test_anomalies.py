"""Anomaly detectors.

Each test plants a defect that was actually found in South Africa's published
school data, and checks the detector catches it. The negative tests matter
equally: a detector that fires on clean data is worse than none, because it
trains whoever reads the report to ignore it.
"""
import pandas as pd
import pytest

from src.eda import anomalies


def panel(rows):
    return pd.DataFrame(rows, columns=["emis", "year", "province", "phase",
                                       "quintile", "learners", "educators",
                                       "lat", "lon", "nofee", "urbanrural",
                                       "status", "sector"])


def healthy(n=60, year=2020, province="WC", learners=500):
    return [(f"S{i}", year, province, "SECONDARY", "3", learners, 20,
             -33.9, 18.4, "NO_FEE", "URBAN", "OPEN", "PUBLIC") for i in range(n)]


def test_catches_a_year_that_collapses_and_recovers():
    # 2017 lost 1.4 million learners nationally and got them back in 2018.
    rows = healthy(50, 2016, learners=500) + healthy(50, 2017, learners=250) \
        + healthy(50, 2018, learners=500)
    found = anomalies.collapsing_totals(panel(rows))
    assert len(found) >= 1
    assert (found["severity"] == "HIGH").all()


def test_ignores_ordinary_year_on_year_movement():
    rows = healthy(50, 2016, learners=500) + healthy(50, 2017, learners=505)
    assert anomalies.collapsing_totals(panel(rows)).empty


def test_catches_a_province_published_under_two_codes():
    # KZ and KZN turn a country of nine provinces into a dataset of eleven.
    rows = healthy(30, province="KZ") + healthy(30, province="KZN")
    rows += [(f"X{i}", 2020, p, "SECONDARY", "3", 500, 20, -33.9, 18.4,
              "NO_FEE", "URBAN", "OPEN", "PUBLIC")
             for i, p in enumerate(["EC", "FS", "GP", "LP", "MP", "NW", "NC", "WC"])]
    found = anomalies.unstable_categories(panel(rows))
    assert "province" in set(found["finding"].str.extract(r"'(\w+)'")[0])


def test_catches_one_funding_band_spelled_two_ways():
    rows = [(f"S{i}", 2020, "WC", "SECONDARY", q, 500, 20, -33.9, 18.4,
             "NO_FEE", "URBAN", "OPEN", "PUBLIC")
            for i, q in enumerate(["1", "2", "3", "4", "5", "Q1", "Q2", "Q3", "NQ4"])]
    found = anomalies.unstable_categories(panel(rows))
    assert any("quintile" in f for f in found["finding"])


def test_does_not_fire_when_categories_are_clean():
    found = anomalies.unstable_categories(panel(healthy(40)))
    assert found.empty


def test_catches_a_school_that_changes_type():
    rows = [("A", 2016, "WC", "COMBINED", "3", 500, 20, -33.9, 18.4,
             "NO_FEE", "URBAN", "OPEN", "PUBLIC"),
            ("A", 2023, "WC", "PRIMARY", "3", 500, 20, -33.9, 18.4,
             "NO_FEE", "URBAN", "OPEN", "PUBLIC")]
    assert not anomalies.label_churn(panel(rows)).empty


def test_ignores_a_school_whose_type_is_stable():
    rows = [("A", y, "WC", "SECONDARY", "3", 500, 20, -33.9, 18.4,
             "NO_FEE", "URBAN", "OPEN", "PUBLIC") for y in (2016, 2020, 2023)]
    assert anomalies.label_churn(panel(rows)).empty


def test_catches_schools_in_the_atlantic_ocean():
    rows = healthy(10)
    rows += [("Z", 2020, "WC", "SECONDARY", "3", 500, 20, 0, 0,
              "NO_FEE", "URBAN", "OPEN", "PUBLIC")]
    found = anomalies.impossible_values(panel(rows))
    assert any("zero" in f for f in found["finding"])
    assert (found[found["finding"].str.contains("zero")]["severity"] == "HIGH").all()


def test_catches_an_implausible_class_size():
    rows = healthy(10)
    rows += [("Z", 2020, "WC", "SECONDARY", "3", 5000, 2, -33.9, 18.4,
              "NO_FEE", "URBAN", "OPEN", "PUBLIC")]
    found = anomalies.impossible_values(panel(rows))
    assert any("per educator" in f for f in found["finding"])


def test_catches_a_province_that_vanishes_for_a_year():
    # Northern Cape has no 2025 data: a Word template was published into the
    # slot where the spreadsheet should have been.
    rows = healthy(40, 2024, "NC") + healthy(40, 2023, "NC") + healthy(40, 2025, "WC")
    found = anomalies.coverage_gaps(panel(rows))
    assert any("NC" in f for f in found["finding"])


def test_catches_a_school_that_disappears_and_returns():
    rows = [("A", y, "WC", "SECONDARY", "3", 500, 20, -33.9, 18.4,
             "NO_FEE", "URBAN", "OPEN", "PUBLIC") for y in (2015, 2016, 2022, 2023)]
    assert not anomalies.identifier_breaks(panel(rows)).empty


def test_catches_the_same_school_twice_in_one_year():
    rows = [("A", 2020, "WC", "SECONDARY", "3", 500, 20, -33.9, 18.4,
             "NO_FEE", "URBAN", "OPEN", "PUBLIC")] * 2
    assert not anomalies.duplicate_records(panel(rows)).empty


def test_scan_ranks_high_severity_first():
    rows = healthy(30, 2016, learners=500) + healthy(30, 2017, learners=200)
    rows += [("Z", 2020, "WC", "SECONDARY", "3", 500, 20, 0, 0,
              "NO_FEE", "URBAN", "OPEN", "PUBLIC")]
    found = anomalies.scan(panel(rows))
    assert found["severity"].iloc[0] == "HIGH"
    assert list(found["severity"]) == sorted(
        found["severity"], key=lambda s: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[s])


def test_a_failing_detector_does_not_stop_the_scan():
    # Missing columns must degrade to a finding, never to an exception - a scan
    # that dies on one bad field reports nothing about the other six.
    found = anomalies.scan(pd.DataFrame({"emis": ["A"], "year": [2020]}))
    assert isinstance(found, pd.DataFrame)


def test_summary_counts_by_severity():
    rows = healthy(30, 2016, learners=500) + healthy(30, 2017, learners=200)
    s = anomalies.summary(anomalies.scan(panel(rows)))
    assert s["high"] >= 1
    assert s["total_findings"] == s["high"] + s["medium"] + s["low"]
