"""Guards on the training table.

Each assertion here corresponds to a real defect found in the source data that
raised no error at the time. They exist to stop those defects returning.
"""
import csv
import os
import pytest
from src.common.paths import MODEL_TABLE

if not os.path.exists(MODEL_TABLE):
    pytest.skip("model_table.csv not built yet", allow_module_level=True)

ROWS = list(csv.DictReader(open(MODEL_TABLE, encoding="utf-8")))


def test_table_is_not_suspiciously_small():
    # A silent column-name mismatch once cut 3,000 schools without erroring.
    assert len(ROWS) > 150_000


def test_exactly_nine_provinces():
    # KZ/KZN and GT/GP once split the country into eleven.
    provinces = {r["province"] for r in ROWS if r["province"]}
    assert len(provinces) == 9, sorted(provinces)


def test_quintile_is_normalised():
    # Source publishes both "3" and "Q3"; a model reads those as different.
    values = {r["quintile"] for r in ROWS if r["quintile"]}
    assert values <= {"1", "2", "3", "4", "5"}, sorted(values)


def test_only_schools_that_can_have_a_matric_cohort():
    phases = {r["phase"] for r in ROWS}
    assert all("SECONDARY" in p or "COMBINED" in p for p in phases), sorted(phases)


def test_every_row_has_learners():
    # Enrolment is the denominator of the label; a blank one is unusable.
    assert all(r["learners"] and int(r["learners"]) > 0 for r in ROWS)


def test_covers_the_full_year_range():
    years = {int(r["year"]) for r in ROWS}
    assert min(years) <= 2008 and max(years) >= 2024
    # 2019 vanished once because that year spells the key column differently.
    assert 2019 in years
