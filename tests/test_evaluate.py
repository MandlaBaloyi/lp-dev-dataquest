"""Evaluation metrics.

The arithmetic is simple enough that errors here are silent rather than loud:
a transposed confusion matrix or a decile table sorted the wrong way round
still prints plausible numbers, and would misdirect whoever reads them.
"""
import numpy as np
import pandas as pd
import pytest

from src.model import evaluate


def test_confusion_counts_each_cell():
    truth = [1, 1, 0, 0, 1, 0]
    predicted = [1, 0, 1, 0, 1, 0]
    c = evaluate.confusion(truth, predicted)
    assert c == {"true_positive": 2, "false_negative": 1,
                 "false_positive": 1, "true_negative": 2}


def test_confusion_frame_is_not_transposed():
    # Rows are truth, columns are prediction. Transposed, it would swap the
    # false positives and false negatives - which carry very different costs.
    truth = [1, 0, 0, 0]
    predicted = [0, 1, 0, 0]
    frame = evaluate.confusion_frame(truth, predicted)
    assert frame.loc["actually lost learners", "predicted stable"] == 1
    assert frame.loc["actually stable", "predicted at risk"] == 1


def test_recall_and_precision_are_not_swapped():
    # Two real losses, one caught; two flags raised, one right.
    truth = [1, 1, 0, 0]
    probability = [0.9, 0.1, 0.8, 0.2]
    m = evaluate.at_threshold(truth, probability, 0.5)
    assert m["recall"] == pytest.approx(0.5)
    assert m["precision"] == pytest.approx(0.5)


def test_f2_weights_recall_above_precision():
    # Same counts, mirrored: the version that catches more should score higher
    # on F2, which is the whole reason for preferring it here.
    high_recall = evaluate.at_threshold([1, 1, 0, 0, 0, 0], [.9, .9, .9, .9, .1, .1], 0.5)
    high_precision = evaluate.at_threshold([1, 1, 0, 0, 0, 0], [.9, .1, .1, .1, .1, .1], 0.5)
    assert high_recall["recall"] > high_precision["recall"]
    assert high_recall["f2"] > high_precision["f2"]


def test_flagging_everything_scores_zero_on_youden():
    # The degenerate solution an earlier threshold rule actually chose.
    truth = [1] * 20 + [0] * 80
    m = evaluate.at_threshold(truth, [0.9] * 100, 0.5)
    assert m["recall"] == 1.0
    assert m["youden_j"] == pytest.approx(0.0)


def test_deciles_run_from_highest_risk_down():
    rng = np.random.default_rng(0)
    probability = rng.random(1000)
    truth = (rng.random(1000) < probability).astype(int)   # risk is real
    table = evaluate.deciles(truth, probability)
    assert table.loc[1, "loss_rate"] > table.loc[10, "loss_rate"]
    assert table.loc[1, "lift"] > 1


def test_cumulative_recall_reaches_one():
    rng = np.random.default_rng(1)
    truth = rng.integers(0, 2, 500)
    table = evaluate.deciles(truth, rng.random(500))
    assert table["cumulative_recall"].iloc[-1] == pytest.approx(1.0, abs=1e-6)


def test_calibration_is_close_when_risk_is_honest():
    rng = np.random.default_rng(2)
    probability = rng.random(4000)
    truth = (rng.random(4000) < probability).astype(int)
    gaps = evaluate.calibration(truth, probability)["gap"].abs()
    assert gaps.max() < 0.12


def test_calibration_exposes_an_overconfident_model():
    # Predicts 90% risk everywhere; only 10% actually happen.
    truth = [1] * 100 + [0] * 900
    probability = [0.9] * 1000
    assert evaluate.calibration(truth, probability)["gap"].abs().max() > 0.5


def test_ks_is_zero_when_the_score_is_meaningless():
    rng = np.random.default_rng(3)
    truth = rng.integers(0, 2, 4000)
    assert evaluate.ks(truth, rng.random(4000)) < 0.1


def test_ks_is_large_when_the_score_separates_perfectly():
    truth = [0] * 500 + [1] * 500
    probability = [0.1] * 500 + [0.9] * 500
    assert evaluate.ks(truth, probability) == pytest.approx(1.0)
