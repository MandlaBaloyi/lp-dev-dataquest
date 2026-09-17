"""Train the random forest benchmark and record what interpretability costs.

    python -m src.model.benchmark

Produces outputs/forest_metrics.json and outputs/forest_scores.csv, which the
final model page reads to show the scorecard against a model that ranks better
and cannot explain itself.

WHY A BENCHMARK THAT IS NOT SHIPPED

The forest reaches a higher AUC than the scorecard. It is still not the
deliverable, because it cannot tell a school why it was flagged, and the output
of this system directs public money. Reporting only the model we ship would
hide that trade-off; measuring it makes the choice defensible rather than
merely asserted.

WHY IT TRAINS THROUGH 2018

An outcome for year Y is measured from enrolment at Y to Y+2, and the first
test row is 2021. Training through 2018 - whose outcome settles in 2020 - is
therefore clean. Training through 2019 or 2020 is not: the model would have
seen enrolment from inside the test window, which lifts AUC to 0.706 and 0.711
and means nothing.

The threshold is fitted on 2018 alone, the only year late enough to be
informative and early enough to be untouched by the test period.
"""
import json

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from src.common.data import load_model_frame
from src.common.paths import out
from src.model import evaluate
from src.model.features import SPLITS
from src.model.train import CAT, NUM

TRAIN_THROUGH = 2018
THRESHOLD_YEAR = 2018
TARGET_RECALL = 0.70

# 200 trees rather than 600: measured difference is inside the noise and the
# run costs a third as much. Two cores, so the machine stays usable.
FOREST = dict(n_estimators=200, min_samples_leaf=20, max_features="log2",
              class_weight="balanced_subsample", n_jobs=2, random_state=7)

MISSING_FILL = -999


def design_matrix(frame):
    matrix = pd.get_dummies(frame[NUM + CAT], columns=CAT, dummy_na=True)
    return matrix.loc[:, matrix.nunique(dropna=False) > 1].fillna(MISSING_FILL)


def threshold_for_recall(truth, probability, target=TARGET_RECALL):
    """The highest cut that still catches `target` of the losses."""
    truth, probability = np.asarray(truth), np.asarray(probability)
    order = np.argsort(-probability)
    caught = np.cumsum(truth[order]) / max(truth.sum(), 1)
    at = int(np.searchsorted(caught, target))
    return float(probability[order][min(at, len(order) - 1)])


def run():
    frame = load_model_frame()
    frame = frame[frame["loss"].notna()]

    matrix = design_matrix(frame)
    truth = frame["loss"].values
    years = frame["year"].values

    train = np.isin(years, range(2008, TRAIN_THROUGH + 1))
    test = np.isin(years, list(SPLITS["test"]))
    print(f"forest: {train.sum():,} training rows through {TRAIN_THROUGH}, "
          f"{test.sum():,} test rows")

    # Calibration folds sit inside the training years, so no held-out year is
    # consumed and nothing reaches into the test window. Balanced weights
    # distort probabilities by design; isotonic puts them back on real rates
    # without reordering a single school.
    forest = CalibratedClassifierCV(
        RandomForestClassifier(**FOREST), method="isotonic", cv=3)
    forest.fit(matrix[train], truth[train])

    predicted = forest.predict_proba(matrix[test])[:, 1]
    auc = roc_auc_score(truth[test], predicted)

    at_threshold_year = years == THRESHOLD_YEAR
    threshold = threshold_for_recall(
        truth[at_threshold_year],
        forest.predict_proba(matrix[at_threshold_year])[:, 1])

    metrics = evaluate.at_threshold(truth[test], predicted, threshold)
    deciles = evaluate.deciles(truth[test], predicted)

    record = {
        "auc": round(float(auc), 4),
        "gini": round(2 * float(auc) - 1, 4),
        "ks": round(evaluate.ks(truth[test], predicted), 4),
        "n": int(test.sum()),
        "event_rate": round(float(truth[test].mean()), 4),
        "trained_through": TRAIN_THROUGH,
        "trees": FOREST["n_estimators"],
        **{k: metrics[k] for k in
           ("threshold", "precision", "recall", "specificity", "f1", "f2",
            "accuracy", "balanced_accuracy", "youden_j", "flagged_share",
            "true_positive", "false_positive", "false_negative", "true_negative")},
        "top10_loss_rate": round(float(deciles["loss_rate"].iloc[0]), 4),
        "bottom10_loss_rate": round(float(deciles["loss_rate"].iloc[-1]), 4),
        "top10_lift": round(float(deciles["lift"].iloc[0]), 3),
        "deciles": [round(float(v), 4) for v in deciles["loss_rate"]],
        "cumulative_recall": [round(float(v), 4) for v in deciles["cumulative_recall"]],
    }

    with open(out("forest_metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)

    pd.DataFrame({"emis": frame.loc[test, "emis"].values,
                  "year": years[test],
                  "loss": truth[test],
                  "p": predicted}).to_csv(out("forest_scores.csv"), index=False)

    print(f"  AUC {record['auc']}   lift {record['top10_lift']}x   "
          f"({record['top10_loss_rate']:.1%} vs {record['bottom10_loss_rate']:.1%})")
    print(f"  wrote {out('forest_metrics.json')}")
    print(f"  wrote {out('forest_scores.csv')}")
    return record


if __name__ == "__main__":
    run()
