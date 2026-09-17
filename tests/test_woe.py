"""WoE and IV, including the leakage guard."""
import numpy as np
import pandas as pd

from src.eda import woe


def test_iv_is_near_zero_for_a_useless_feature():
    rng = np.random.default_rng(0)
    feature = rng.choice(["a", "b", "c"], 3000)
    target = rng.integers(0, 2, 3000)
    assert woe.information_value(pd.Series(feature), pd.Series(target)) < 0.02


def test_iv_is_high_for_a_feature_that_determines_the_target():
    target = np.array([0, 1] * 1500)
    feature = np.where(target == 1, "bad", "good")
    assert woe.information_value(pd.Series(feature), pd.Series(target)) > 0.5


def test_woe_pushes_in_opposite_directions_for_opposite_bins():
    target = np.array([0, 1] * 1500)
    feature = np.where(target == 1, "bad", "good")
    table = woe.woe_table(pd.Series(feature), pd.Series(target))
    by_bin = dict(zip(table["bin"], table["woe"]))
    assert by_bin["good"] > 0 > by_bin["bad"]


def test_encoder_applies_training_bins_to_unseen_data():
    # The guard against leakage: transform must not refit.
    train = pd.DataFrame({"q": ["1", "2", "3"] * 100})
    target = pd.Series([1, 0, 0] * 100)
    encoder = woe.WoEEncoder().fit(train, target)

    test = pd.DataFrame({"q": ["1", "2", "3", "99"]})   # 99 unseen in training
    out = encoder.transform(test)

    assert list(out.columns) == ["woe_q"]
    assert out["woe_q"].iloc[3] == 0.0                  # unseen -> neutral, not an error


def test_missing_values_become_their_own_bin():
    feature = pd.Series(["a", "b", None, None] * 100)
    target = pd.Series([1, 0, 1, 0] * 100)
    table = woe.woe_table(feature, target)
    assert "UNKNOWN" in set(table["bin"])
