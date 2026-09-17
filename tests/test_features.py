"""Feature construction.

The tests that matter here are the ones about time. A feature that reaches
forward into the year it predicts produces a model that tests beautifully and
is useless on a cohort still in school - and nothing about it raises an error.
"""
import numpy as np
import pandas as pd
import pytest

from src.model import features


def panel(rows):
    return pd.DataFrame(rows, columns=["emis", "year", "learners", "educators",
                                       "province", "district", "phase", "lat", "lon"])


def series(emis, start, values, **kw):
    return [(emis, start + i, v, 20, kw.get("prov", "WC"),
             kw.get("dist", "D1"), "SECONDARY", -33.9, 18.4)
            for i, v in enumerate(values)]


def test_enrolment_change_looks_backwards_only():
    frame = features.build(panel(series("1", 2015, [100, 110, 121])))
    frame = frame.set_index("year")
    assert frame.loc[2016, "enrolment_change_1y"] == pytest.approx(0.10)
    assert frame.loc[2017, "enrolment_change_1y"] == pytest.approx(0.10)


def test_first_year_has_no_change_to_report():
    frame = features.build(panel(series("1", 2015, [100, 110])))
    assert pd.isna(frame.set_index("year").loc[2015, "enrolment_change_1y"])


def test_volatility_excludes_the_current_year():
    # The current year's own enrolment must not inform its own volatility.
    steady = features.build(panel(series("s", 2010, [100] * 6)))
    swinging = features.build(panel(series("v", 2010, [100, 300, 90, 280, 110, 260])))
    assert steady["enrolment_volatility"].iloc[-1] < swinging["enrolment_volatility"].iloc[-1]


def test_ratio_uses_learners_over_educators():
    frame = features.build(panel([("1", 2020, 400, 20, "WC", "D1", "SECONDARY", -33.9, 18.4)]))
    assert frame["learner_educator_ratio"].iloc[0] == pytest.approx(20.0)


def test_zero_educators_does_not_blow_up():
    frame = features.build(panel([("1", 2020, 400, 0, "WC", "D1", "SECONDARY", -33.9, 18.4)]))
    assert pd.isna(frame["learner_educator_ratio"].iloc[0])


def test_size_is_measured_against_the_district():
    rows = [("big", 2020, 900, 30, "WC", "D1", "SECONDARY", -33.9, 18.4),
            ("mid", 2020, 300, 10, "WC", "D1", "SECONDARY", -33.9, 18.4),
            ("sml", 2020, 100, 5, "WC", "D1", "SECONDARY", -33.9, 18.4)]
    frame = features.build(panel(rows)).set_index("emis")
    assert frame.loc["big", "size_vs_district"] > 1
    assert frame.loc["sml", "size_vs_district"] < 1


def test_school_age_counts_from_first_appearance():
    frame = features.build(panel(series("1", 2012, [100, 100, 100])))
    assert list(frame["school_age"]) == [0, 1, 2]


def test_latitude_zero_yields_no_distance():
    rows = [("atlantic", 2020, 400, 20, "WC", "D1", "SECONDARY", 0, 0),
            ("real", 2020, 400, 20, "WC", "D1", "SECONDARY", -33.9, 18.4)]
    frame = features.build(panel(rows)).set_index("emis")
    assert pd.isna(frame.loc["atlantic", "distance_to_city_km"])
    assert frame.loc["real", "distance_to_city_km"] < 50


def test_distance_grows_with_remoteness():
    near = features.distance_to_city(pd.Series([-33.92]), pd.Series([18.42]))
    far = features.distance_to_city(pd.Series([-28.50]), pd.Series([21.20]))
    assert near.iloc[0] < far.iloc[0]


def test_training_table_pairs_outcomes_with_earlier_features():
    # The outcome is at 2022; the features it gets must be the 2020 ones.
    rows = series("1", 2018, [500, 520, 540, 560, 580])
    labels = pd.DataFrame([{"emis": "1", "year": 2022, "is_high_risk": 1,
                            "survival_index": 0.5, "throughput": 0.1,
                            "wrote": 50, "enrolment_before": 540}])
    table = features.training_table(panel(rows), labels, lag=2)
    assert len(table) == 1
    # 2020 enrolment was 540, up from 520 in 2019: a 1-year change of ~3.8%.
    assert table["enrolment_change_1y"].iloc[0] == pytest.approx(540 / 520 - 1)


def test_training_table_drops_outcomes_with_no_earlier_features():
    rows = series("1", 2022, [500])
    labels = pd.DataFrame([{"emis": "1", "year": 2022, "is_high_risk": 1,
                            "survival_index": 0.5, "throughput": 0.1,
                            "wrote": 50, "enrolment_before": 500}])
    # Features would have to come from 2020, which does not exist.
    assert features.training_table(panel(rows), labels, lag=2).empty
