"""Guards on the independent track: the two silent mistakes named in the
brief, plus the cleaning and feature rules that would fail without erroring.

    python -m pytest independent/tests -v
"""
import numpy as np
import pandas as pd
import pytest

from src.eda import woe
from src.build.clean import fix_coordinate
from src.model.features import HORIZON, SPLITS, build
from src.model.train import describe_bin, threshold_for_recall


# ------------------------------------------------ mistake 1: splitting

def test_splits_are_by_year_and_outcomes_never_overlap_later_splits():
    train, valid, test = (list(SPLITS[s]) for s in ("train", "valid", "test"))
    # an outcome is observed HORIZON years after its row's year
    assert max(train) + HORIZON <= min(valid)
    assert max(valid) + HORIZON <= min(test)
    assert max(test) + HORIZON <= 2025
    assert not set(train) & set(valid) and not set(valid) & set(test)


def toy_panel():
    rows = []
    for emis, base in ((1, 400), (2, 900)):
        for y in (2012, 2013, 2014, 2015, 2016):
            rows.append({"emis": emis, "year": y, "province": "LP", "district": "D",
                         "district_key": "LP:D", "learners": base + 10 * (y - 2012),
                         "educators": 20.0, "lat": -23.9 + emis / 100, "lon": 29.4,
                         "quintile": 1.0, "nofee": 1.0, "closing_flag": 0,
                         "sector": "PUBLIC", "phase": "SECONDARY", "urbanrural": "RURAL"})
    return pd.DataFrame(rows)


def test_features_do_not_see_the_future():
    a = build(toy_panel())
    changed = toy_panel()
    changed.loc[changed.year == 2016, "learners"] = 5  # only the future changes
    b = build(changed)
    cols = ["chg1", "chg3", "vol", "peak_ratio", "log_learners", "district_chg1", "nearby_chg1"]
    past = (a.year <= 2015).to_numpy()
    pd.testing.assert_frame_equal(
        a.loc[past, cols].reset_index(drop=True), b.loc[past, cols].reset_index(drop=True))
    # ...while the label for 2014 (whose t+2 is 2016) does change
    assert a.loc[a.year == 2014, "chg_t2"].tolist() != b.loc[b.year == 2014, "chg_t2"].tolist()


# ------------------------------------------------ mistake 2: bins on all data

def test_bins_are_frozen_after_fitting():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=2000))
    y = pd.Series((rng.random(2000) < 1 / (1 + np.exp(2 * x))).astype(int))
    b = woe.fit_numeric("x", x, y)
    edges, table = list(b.edges), b.table.copy()
    shifted = pd.Series(rng.normal(loc=3, size=500))
    b.transform(shifted)
    assert b.edges == edges
    pd.testing.assert_frame_equal(b.table, table)


def test_unseen_category_scores_neutral():
    x = pd.Series(["A"] * 50 + ["B"] * 50)
    y = pd.Series([1] * 10 + [0] * 40 + [1] * 30 + [0] * 20)
    b = woe.fit_categorical("c", x, y)
    assert b.transform(pd.Series(["Z"])).iat[0] == 0.0


def test_tiny_missing_bin_is_neutral():
    x = pd.Series([np.nan] * 5 + list(range(995)), dtype=float)
    y = pd.Series([1] * 5 + [0] * 995)
    b = woe.fit_numeric("x", x, y)
    row = b.table[b.table.bin == woe.MISSING]
    assert row.woe.iat[0] == 0.0


def test_woe_sign_convention():
    x = pd.Series(["risky"] * 100 + ["safe"] * 100)
    y = pd.Series([1] * 60 + [0] * 40 + [1] * 5 + [0] * 95)
    t = woe.fit_categorical("c", x, y).table.set_index("bin")
    assert t.woe["safe"] > 0 > t.woe["risky"]


# ------------------------------------------------ cleaning and reporting

@pytest.mark.parametrize("raw, expected", [
    (-26.2041, -26.2041),
    (-262041000.0, -26.2041),
    (0.0, None),
    (float("nan"), None),
    (-9e20, None),
])
def test_fix_coordinate(raw, expected):
    got = fix_coordinate(raw, -35.0, -22.0)
    if expected is None:
        assert np.isnan(got)
    else:
        assert got == pytest.approx(expected)


def test_threshold_reaches_target_recall():
    p = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
    y = np.array([1, 0, 1, 1, 0, 0, 1, 0, 0, 0])
    thr = threshold_for_recall(y, p, 0.75)
    assert thr == 0.6
    assert y[p >= thr].sum() / y.sum() >= 0.75


def test_bin_descriptions_are_readable():
    assert describe_bin("quintile", "[-inf, 3.0)") == "Q1-Q2"
    assert describe_bin("quintile", "[4.0, inf)") == "Q4-Q5"
    assert describe_bin("chg1", "[-inf, -0.113)") == "below -11.3%"
    assert describe_bin("vol", woe.MISSING) == "fewer than four years of history"


# ------------------------------------------------ saved scorecard

def test_saved_scorecard_reproduces_the_published_ranking():
    from src.common.paths import MODEL_FRAME, out
    from src.model.scoring import Scorecard
    rank = pd.read_csv(out("ranking_2025.csv"))
    frame = pd.read_csv(MODEL_FRAME)
    frame = frame[frame.split == "score"].set_index("emis").loc[rank.emis]
    card = Scorecard.load()
    # model.json stores WoE to 4 decimals, so scores agree to within a point
    assert np.abs(card.score(frame).to_numpy() - rank.score.to_numpy()).max() <= 1
    assert np.allclose(card.probability(frame).to_numpy(), rank.p_loss.to_numpy(), atol=1e-3)


# ------------------------------------------------ risk list search

def _search(register, term):
    """The risk list's search, as risk_list.py performs it."""
    return register[
        register.school.str.contains(term, case=False, na=False, regex=False)
        | register.emis.astype(str).str.contains(term, na=False, regex=False)]


def test_search_finds_schools_outside_the_default_tier_filter():
    """The Tier pills default to Priority and Watch, which is under a quarter of
    the register. Search runs against the whole register precisely so the other
    three quarters are findable - previously they returned nothing at all."""
    from src.common.paths import out
    register = pd.read_csv(out("ranking_2025.csv"))
    lower_risk = register[~register.tier.isin(["PRIORITY", "WATCH"])]
    assert len(lower_risk) > 0, "expected schools outside the default tiers"
    assert len(_search(register, lower_risk.iloc[0].school)) >= 1


def test_search_handles_school_names_containing_brackets():
    """23 schools have names like AVIANTO SCHOOL (PTY) LTD. Under the default
    regex=True those are patterns, not names, and searching one raised rather
    than matched."""
    from src.common.paths import out
    register = pd.read_csv(out("ranking_2025.csv"))
    bracketed = register[register.school.str.contains("(", regex=False, na=False)]
    assert len(bracketed) > 0, "expected at least one bracketed school name"
    assert len(_search(register, bracketed.iloc[0].school)) >= 1
    _search(register, "(")          # a bare metacharacter must not raise


def test_search_matches_on_emis_and_ignores_case():
    from src.common.paths import out
    register = pd.read_csv(out("ranking_2025.csv"))
    first = register.iloc[0]
    assert len(_search(register, str(first.emis))) >= 1
    assert len(_search(register, first.school.lower())) >= 1
