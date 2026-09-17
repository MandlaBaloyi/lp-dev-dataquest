"""The merged model: enrolment signals plus matric outcomes.

Keeps the independent track's target and its binning, because both were sound,
and adds what the primary track's matric extraction can say that a learner
headcount cannot.

Everything is tuned on validation. Test is read once, at the end. Tuning
against test is leakage by another name - slower and more flattering than a
bad split, and just as wrong.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from independent.src import woe as iwoe
from independent.src.train import CAT, NUM, fit_lr, select_features
from src.common.paths import OUTPUTS, ensure
from src.model.merged import MATRIC_FEATURES, build

# Built from matric results and district context, none of it derivable from
# the enrolment panel alone.
ENGINEERED = [
    "dist_throughput", "dist_wrote_chg", "throughput_vs_district",
    "edu_chg3", "ler_vol", "small_and_volatile", "prior_loss",
]


def engineer(frame):
    """Add district matric context, staffing instability and prior outcome."""
    frame = frame.sort_values(["emis", "year"]).copy()
    by_school = frame.groupby("emis", sort=False)

    # A district where many schools are shedding matric candidates is a
    # different context from one where they are not, and nothing in the
    # enrolment panel can see it.
    district = (frame.groupby(["district_key", "year"])
                .agg(dist_throughput=("throughput", "median"),
                     dist_wrote_chg=("wrote_chg1", "median")).reset_index())
    frame = frame.merge(district, on=["district_key", "year"], how="left")
    frame["throughput_vs_district"] = (
        frame["throughput"] / frame["dist_throughput"].replace(0, np.nan))

    frame["edu_chg3"] = by_school["educators"].transform(
        lambda s: (s - s.shift(3)) / s.shift(3).replace(0, np.nan))
    frame["ler_vol"] = by_school["ler"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=3).std())

    # A small erratic school is a different risk from a large erratic one, and
    # a linear model cannot express that interaction by itself.
    frame["small_and_volatile"] = (
        frame["vol"] / frame["log_learners"].replace(0, np.nan))

    # The outcome for year Y is observed at Y+2, so at year Y the most recent
    # outcome anyone could know is the one for Y-2. Shifting by two is not
    # look-ahead; it is what a district official already has on file.
    frame["prior_loss"] = by_school["loss"].shift(2)
    return frame


def full_metrics(truth, probability, threshold):
    """Everything a scorecard is normally judged on, not AUC alone.

    AUC scores the whole ranking. Nobody works a whole ranking - they work the
    top of it, so lift in the worst decile is the number that decides whether
    this is usable.
    """
    predicted = (probability >= threshold).astype(int)
    auc = roc_auc_score(truth, probability)

    order = np.argsort(-probability)
    top = order[:max(1, len(order) // 10)]
    bottom = order[-max(1, len(order) // 10):]
    base = truth.mean()

    hits = ((predicted == 1) & (truth == 1)).sum()
    return {
        "auc": round(auc, 4),
        "gini": round(2 * auc - 1, 4),
        "ks": round(ks(truth, probability), 4),
        "recall": round(hits / max(truth.sum(), 1), 4),
        "precision": round(hits / max(predicted.sum(), 1), 4),
        "accuracy": round((predicted == truth).mean(), 4),
        "loss_rate_worst_decile": round(float(truth.iloc[top].mean()), 4),
        "loss_rate_best_decile": round(float(truth.iloc[bottom].mean()), 4),
        "lift_worst_decile": round(float(truth.iloc[top].mean() / base), 3),
        "base_rate": round(float(base), 4),
    }


def ks(truth, probability):
    """Largest gap between the two score distributions."""
    order = np.argsort(probability)
    t = np.asarray(truth)[order]
    positives = np.cumsum(t) / max(t.sum(), 1)
    negatives = np.cumsum(1 - t) / max((1 - t).sum(), 1)
    return float(np.max(np.abs(positives - negatives)))


def threshold_for_recall(truth, probability, target=0.70):
    """Highest cut that still catches `target` of the losses.

    Recall is favoured because a missed school that goes on to lose a fifth of
    its learners costs more than a district visit to a school that turns out
    fine.
    """
    for candidate in np.unique(probability)[::-1]:
        predicted = (probability >= candidate).astype(int)
        if ((predicted == 1) & (truth == 1)).sum() / max(truth.sum(), 1) >= target:
            return float(candidate)
    return 0.5


def run():
    ensure(OUTPUTS)
    frame = engineer(build())
    frame = frame[frame["loss"].notna()]

    train = frame[frame.split == "train"]
    validate = frame[frame.split == "valid"]
    test = frame[frame.split == "test"]

    matric = [c for c in MATRIC_FEATURES if c in frame.columns]
    numeric = NUM + matric + ENGINEERED

    print(f"train {len(train):,}   validate {len(validate):,}   test {len(test):,}")
    print(f"matric data present on {100 * test.has_matric_data.mean():.0f}% of test rows\n")

    bins = iwoe.fit(train, train["loss"], numeric, CAT)
    woe_train = iwoe.transform(train, bins)
    keep, scorecard, dropped = select_features(
        woe_train, train["loss"], iwoe.information_value(bins))

    probability = {
        "validate": scorecard.predict_proba(iwoe.transform(validate, bins)[keep])[:, 1],
        "test": scorecard.predict_proba(iwoe.transform(test, bins)[keep])[:, 1],
    }

    # The tree exists to measure what interpretability costs, not to ship.
    matrix = pd.get_dummies(
        pd.concat([train, validate, test])[numeric + CAT], columns=CAT, dummy_na=True)
    matrix = matrix.loc[:, matrix.nunique(dropna=False) > 1]
    x_train = matrix.iloc[:len(train)]
    x_validate = matrix.iloc[len(train):len(train) + len(validate)]
    x_test = matrix.iloc[len(train) + len(validate):]

    tree = HistGradientBoostingClassifier(max_iter=400, random_state=7)
    tree.fit(x_train, train["loss"])
    tree_probability = {
        "validate": tree.predict_proba(x_validate)[:, 1],
        "test": tree.predict_proba(x_test)[:, 1],
    }

    threshold = threshold_for_recall(validate["loss"], probability["validate"])
    tree_threshold = threshold_for_recall(validate["loss"], tree_probability["validate"])

    results = {
        "scorecard": full_metrics(test["loss"], probability["test"], threshold),
        "tree": full_metrics(test["loss"], tree_probability["test"], tree_threshold),
    }

    print("TEST YEARS 2021-2023")
    print(pd.DataFrame(results).T.to_string())
    print(f"\nvariables kept ({len(keep)}): {keep}")
    print(f"of which from the merge: {[c for c in keep if c in matric + ENGINEERED]}")

    with open(os.path.join(OUTPUTS, "merged_metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    register = test[["emis", "year", "school", "province", "district",
                     "quintile", "learners", "loss"]].copy()
    register["risk"] = probability["test"]
    register = register.sort_values("risk", ascending=False)
    register["rank"] = range(1, len(register) + 1)
    register.to_csv(os.path.join(OUTPUTS, "merged_register.csv"), index=False)
    print(f"\nwrote {OUTPUTS}")

    return results


if __name__ == "__main__":
    run()
