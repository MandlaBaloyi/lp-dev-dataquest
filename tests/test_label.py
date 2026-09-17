"""The target variable.

The target decides what the model learns, so the properties tested here are
the ones that would quietly corrupt everything downstream: enrolment matched
to the wrong year, schools of different phases compared directly, or a
threshold that means something different in 2012 than in 2024.
"""
import pandas as pd
import pytest

from src.model import label


def panel(rows):
    return pd.DataFrame(rows, columns=["emis", "year", "learners", "phase"])


def results(rows):
    return pd.DataFrame(rows, columns=["emis", "year", "wrote"])


def test_matches_matric_year_to_enrolment_two_years_earlier():
    # 400 learners in 2020, 80 wrote in 2022 -> throughput 0.2 against 2020.
    frame = label.build(
        panel([("1", 2020, 400, "SECONDARY"), ("1", 2022, 200, "SECONDARY")]),
        results([("1", 2022, 80)]),
    )
    assert len(frame) == 1
    assert frame["enrolment_before"].iloc[0] == 400
    assert frame["throughput"].iloc[0] == pytest.approx(0.2)


def test_a_shrinking_school_is_not_flattered_by_the_lag():
    # Same matric class, but one school halved its enrolment over the period.
    # Dividing by today's smaller roll would hide exactly that loss.
    frame = label.build(
        panel([("stable", 2020, 400, "SECONDARY"), ("stable", 2022, 400, "SECONDARY"),
               ("shrunk", 2020, 800, "SECONDARY"), ("shrunk", 2022, 400, "SECONDARY")]),
        results([("stable", 2022, 80), ("shrunk", 2022, 80)]),
    ).set_index("emis")
    assert frame.loc["shrunk", "throughput"] < frame.loc["stable", "throughput"]


def test_drops_a_year_with_no_matching_enrolment():
    frame = label.build(
        panel([("1", 2020, 400, "SECONDARY")]),
        results([("1", 2030, 80)]),
    )
    assert frame.empty


def test_index_compares_schools_only_against_their_own_phase():
    # Identical throughput, different phase. Each is typical for its own kind,
    # so both should index at 1.0 rather than one appearing to fail.
    rows, res = [], []
    for i in range(6):
        phase = "SECONDARY" if i < 3 else "COMBINED"
        rows += [(str(i), 2020, 500, phase), (str(i), 2022, 500, phase)]
        res.append((str(i), 2022, 100))
    frame = label.build(panel(rows), results(res))
    assert frame["survival_index"].round(3).eq(1.0).all()


def test_flags_roughly_a_fifth_as_high_risk():
    rows, res = [], []
    for i in range(100):
        rows += [(str(i), 2020, 500, "SECONDARY"), (str(i), 2022, 500, "SECONDARY")]
        res.append((str(i), 2022, 40 + i))      # a spread of outcomes
    frame = label.build(panel(rows), results(res))
    assert 0.15 <= frame["is_high_risk"].mean() <= 0.25


def test_the_worst_schools_are_the_ones_flagged():
    rows, res = [], []
    for i in range(50):
        rows += [(str(i), 2020, 500, "SECONDARY"), (str(i), 2022, 500, "SECONDARY")]
        res.append((str(i), 2022, 20 + i * 4))
    frame = label.build(panel(rows), results(res))
    flagged = frame[frame["is_high_risk"] == 1]["survival_index"].max()
    clear = frame[frame["is_high_risk"] == 0]["survival_index"].min()
    assert flagged <= clear


def test_threshold_is_applied_within_each_year():
    # A year where every school does badly should still flag about a fifth,
    # not all of them - otherwise a nationally hard year reads as mass failure.
    rows, res = [], []
    for year, scale in ((2022, 100), (2024, 20)):
        for i in range(40):
            rows += [(f"{year}_{i}", year - 2, 500, "SECONDARY")]
            res.append((f"{year}_{i}", year, scale + i))
    frame = label.build(panel(rows), results(res))
    by_year = frame.groupby("year")["is_high_risk"].mean()
    assert by_year.between(0.1, 0.3).all()


def test_ignores_schools_too_small_to_measure():
    # In a school of 20, one learner moves the rate by five points.
    frame = label.build(
        panel([("tiny", 2020, 20, "SECONDARY")]),
        results([("tiny", 2022, 12)]),
    )
    assert frame.empty


def test_ignores_a_handful_of_candidates():
    frame = label.build(
        panel([("1", 2020, 400, "SECONDARY")]),
        results([("1", 2022, 3)]),
    )
    assert frame.empty
