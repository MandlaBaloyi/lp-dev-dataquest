"""Training the risk scorecard, and a benchmark to measure what it costs.

THE SPLIT IS BY YEAR, AND THAT IS NOT A DETAIL

    train      2009-2020
    validate   2021-2022
    test       2023-2024

A school appears in up to sixteen rows here, one per year. Split at random and
a school's 2019 row trains the model while its 2021 row tests it - the model
then scores well by recognising schools it has already seen rather than by
learning anything that transfers to a school it has not. Nothing errors. The
metrics come back excellent. The model is useless on the only cohort anyone
can still help.

Splitting by year also matches how the thing would really be used: fitted on
history, applied to a year that has not finished yet.

WEIGHT OF EVIDENCE IS FITTED ON TRAINING YEARS ONLY

The same discipline applies to the encoding. Bins learned across all years have
already seen the test set, which inflates every metric downstream without
raising anything. WoEEncoder separates fit from transform precisely so that
applying training bins to later years is the easy path.

TWO MODELS, ONE OF THEM TO SHIP

The scorecard is a logistic regression over WoE-binned features. Every score it
produces decomposes into visible weights, so a school's ranking can be
explained line by line to whoever has to act on it.

Gradient boosting runs alongside it, not to ship but to answer one question:
how much accuracy does interpretability cost? If the gap is small the choice is
easy. If it is large, that is worth reporting rather than hiding.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)

from src.common.paths import OUTPUTS, PROCESSED, ensure
from src.eda.woe import WoEEncoder, rank_by_iv

TRAIN_YEARS = (2009, 2020)
VALIDATE_YEARS = (2021, 2022)
TEST_YEARS = (2023, 2024)

FEATURES = [
    "enrolment_change_1y", "enrolment_change_3y", "enrolment_change_5y",
    "enrolment_volatility", "learner_educator_ratio",
    "ratio_vs_province", "school_age", "distance_to_city_km",
    "quintile", "nofee", "urbanrural", "province", "phase",
]

TARGET = "is_high_risk"

# A register nobody can act on is not a register. Flagging beyond this share
# of schools stops being a shortlist and starts being a directory.
MAX_FLAGGED_SHARE = 0.35


def split(table):
    """Three disjoint spans of years. No school-year appears in two of them."""
    year = pd.to_numeric(table["year"], errors="coerce")
    return (
        table[year.between(*TRAIN_YEARS)],
        table[year.between(*VALIDATE_YEARS)],
        table[year.between(*TEST_YEARS)],
    )


def metrics(truth, predicted_probability, threshold):
    """Everything reported, at one decision threshold.

    Accuracy is included because it is expected, and listed last because on a
    target that is 20% positive by construction, predicting "no risk" for every
    school scores 80% while identifying nobody.
    """
    predicted = (predicted_probability >= threshold).astype(int)
    auc = roc_auc_score(truth, predicted_probability)
    return {
        "auc": round(auc, 4),
        "gini": round(2 * auc - 1, 4),          # the same information as AUC
        "precision": round(precision_score(truth, predicted, zero_division=0), 4),
        "recall": round(recall_score(truth, predicted, zero_division=0), 4),
        "f1": round(f1_score(truth, predicted, zero_division=0), 4),
        "accuracy": round(accuracy_score(truth, predicted), 4),
        "flagged": int(predicted.sum()),
        "positives": int(truth.sum()),
    }


def choose_threshold(truth, probability, max_flagged=MAX_FLAGGED_SHARE):
    """Pick the cut by Youden's J, capped on how much it may flag.

    An earlier version maximised recall plus precision subject to precision
    beating the base rate. That degenerates: flagging every school scores
    perfect recall and precision exactly equal to the base rate, which passes
    the test and wins. The model then "identified" 12,072 of 12,082 schools,
    which is not a shortlist, it is the phone book.

    Youden's J - recall plus specificity minus one - cannot be gamed that way,
    because flagging everything drives specificity to zero.

    The cap is a practical constraint rather than a statistical one. A register
    is only useful if someone can act on it, and nobody can act on a third of
    the schools in the country.
    """
    best, best_score = 0.5, -1.0
    positives = max(truth.sum(), 1)
    negatives = max((1 - truth).sum(), 1)

    for candidate in np.arange(0.05, 0.95, 0.01):
        predicted = (probability >= candidate).astype(int)
        if predicted.mean() > max_flagged or predicted.sum() == 0:
            continue
        recall = ((predicted == 1) & (truth == 1)).sum() / positives
        specificity = ((predicted == 0) & (truth == 0)).sum() / negatives
        youden = recall + specificity - 1
        if youden > best_score:
            best, best_score = float(candidate), youden
    return best


def run(table):
    ensure(OUTPUTS)
    train, validate, test = split(table)
    print(f"train    {len(train):>7,} rows  {TRAIN_YEARS[0]}-{TRAIN_YEARS[1]}")
    print(f"validate {len(validate):>7,} rows  {VALIDATE_YEARS[0]}-{VALIDATE_YEARS[1]}")
    print(f"test     {len(test):>7,} rows  {TEST_YEARS[0]}-{TEST_YEARS[1]}")

    overlap = set(train["emis"]) & set(test["emis"])
    print(f"\nschools in both train and test: {len(overlap):,}")
    print("  (expected - the same schools persist across years. The split is by")
    print("   year, so no school-YEAR is ever in two sets, which is what matters.)")

    features = [f for f in FEATURES if f in table.columns]

    # Information value first, so what enters the model is justified.
    iv = rank_by_iv(train[features], train[TARGET])
    print("\nINFORMATION VALUE (training years only)")
    print(iv.to_string(index=False))
    iv.to_csv(os.path.join(OUTPUTS, "information_value.csv"), index=False)

    # Fitted on training years, applied unchanged to later years.
    encoder = WoEEncoder(bins=10).fit(train[features], train[TARGET])
    x_train = encoder.transform(train[features])
    x_validate = encoder.transform(validate[features])
    x_test = encoder.transform(test[features])

    results = {}

    scorecard = LogisticRegression(max_iter=2000, C=1.0)
    scorecard.fit(x_train, train[TARGET])
    threshold = choose_threshold(validate[TARGET],
                                 scorecard.predict_proba(x_validate)[:, 1])
    results["scorecard"] = metrics(test[TARGET],
                                   scorecard.predict_proba(x_test)[:, 1], threshold)
    results["scorecard"]["threshold"] = round(threshold, 3)

    benchmark = HistGradientBoostingClassifier(max_iter=300, random_state=0)
    benchmark.fit(x_train, train[TARGET])
    bench_threshold = choose_threshold(validate[TARGET],
                                       benchmark.predict_proba(x_validate)[:, 1])
    results["benchmark"] = metrics(test[TARGET],
                                   benchmark.predict_proba(x_test)[:, 1], bench_threshold)
    results["benchmark"]["threshold"] = round(bench_threshold, 3)

    print("\nTEST YEARS 2023-2024")
    frame = pd.DataFrame(results).T
    print(frame.to_string())

    gap = results["benchmark"]["auc"] - results["scorecard"]["auc"]
    print(f"\ninterpretability costs {gap:+.4f} AUC")

    weights = (pd.DataFrame({"feature": x_train.columns,
                             "weight": scorecard.coef_[0]})
               .assign(absolute=lambda d: d.weight.abs())
               .sort_values("absolute", ascending=False)
               .drop(columns="absolute"))
    print("\nSCORECARD WEIGHTS")
    print(weights.round(4).to_string(index=False))
    weights.to_csv(os.path.join(OUTPUTS, "scorecard_weights.csv"), index=False)

    with open(os.path.join(OUTPUTS, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    # The register: every school in the test years, ranked by risk.
    register = test[["emis", "year", "province", "quintile", "survival_index",
                     "wrote", "enrolment_before", TARGET]].copy()
    register["risk"] = scorecard.predict_proba(x_test)[:, 1]
    register = register.sort_values("risk", ascending=False)
    register["rank"] = range(1, len(register) + 1)
    register.to_csv(os.path.join(OUTPUTS, "risk_register.csv"), index=False)
    print(f"\nwrote {OUTPUTS}\\risk_register.csv  ({len(register):,} rows)")

    return results, weights, register


def main():
    table = pd.read_csv(os.path.join(PROCESSED, "training_table.csv"),
                        dtype={"emis": str})
    run(table)


if __name__ == "__main__":
    main()
