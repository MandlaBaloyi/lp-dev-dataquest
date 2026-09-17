"""Everything a risk model should be judged on, not AUC alone.

AUC scores the whole ranking. Nobody works a whole ranking - a district works
the top of it, with the staff and budget it has. So the decile table and the
confusion matrix say more about whether this is usable than AUC does.

Four things are reported, and each answers a different question:

    confusion matrix   what happens to real schools at the chosen cut
    threshold metrics  precision, recall and the rest at that cut
    decile table       how loss concentrates towards the top of the ranking
    calibration        whether a predicted 20% risk really means 20%

Calibration matters here and is usually skipped. A model can rank perfectly
and still be badly calibrated, and the moment anyone reads a score as "this
school has a 30% chance", calibration is what makes that sentence true or
false.
"""
import numpy as np
import pandas as pd


def confusion(truth, predicted):
    """Counts, and what each cell costs in this setting."""
    truth = np.asarray(truth).astype(int)
    predicted = np.asarray(predicted).astype(int)
    tp = int(((predicted == 1) & (truth == 1)).sum())
    fp = int(((predicted == 1) & (truth == 0)).sum())
    fn = int(((predicted == 0) & (truth == 1)).sum())
    tn = int(((predicted == 0) & (truth == 0)).sum())
    return {"true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn}


def confusion_frame(truth, predicted):
    """The matrix as a table, labelled for a reader who is not a statistician."""
    c = confusion(truth, predicted)
    return pd.DataFrame(
        [[c["true_negative"], c["false_positive"]],
         [c["false_negative"], c["true_positive"]]],
        index=["actually stable", "actually lost learners"],
        columns=["predicted stable", "predicted at risk"])


def at_threshold(truth, probability, threshold):
    """Every headline metric at one decision cut."""
    truth = np.asarray(truth).astype(int)
    predicted = (np.asarray(probability) >= threshold).astype(int)
    c = confusion(truth, predicted)
    tp, fp, fn, tn = (c["true_positive"], c["false_positive"],
                      c["false_negative"], c["true_negative"])

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)

    return {
        "threshold": round(float(threshold), 4),
        "flagged": int(predicted.sum()),
        "flagged_share": round(float(predicted.mean()), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "f1": round(2 * precision * recall / max(precision + recall, 1e-9), 4),
        # Recall weighted four times precision: a school missed gets nothing,
        # a school wrongly flagged gets a visit it did not quite need.
        "f2": round(5 * precision * recall / max(4 * precision + recall, 1e-9), 4),
        "accuracy": round((tp + tn) / max(len(truth), 1), 4),
        "balanced_accuracy": round((recall + specificity) / 2, 4),
        "youden_j": round(recall + specificity - 1, 4),
        **c,
    }


def deciles(truth, probability, groups=10):
    """How loss concentrates towards the top of the ranking.

    This is the table a planner reads: work the first row and you are right
    this often, against the base rate.
    """
    frame = pd.DataFrame({"truth": np.asarray(truth).astype(int),
                          "probability": np.asarray(probability)})
    frame = frame.sort_values("probability", ascending=False).reset_index(drop=True)
    frame["decile"] = (frame.index * groups // len(frame)) + 1

    base = frame["truth"].mean()
    table = (frame.groupby("decile")
             .agg(schools=("truth", "size"),
                  losses=("truth", "sum"),
                  loss_rate=("truth", "mean"),
                  mean_score=("probability", "mean")))
    table["lift"] = table["loss_rate"] / base
    table["cumulative_recall"] = table["losses"].cumsum() / max(frame["truth"].sum(), 1)
    return table.round(4)


def calibration(truth, probability, bins=10):
    """Does a predicted risk of 20% actually happen 20% of the time?"""
    frame = pd.DataFrame({"truth": np.asarray(truth).astype(int),
                          "probability": np.asarray(probability)})
    # A model that returns one probability for every school cannot be cut into
    # quantiles: qcut returns all-NaN rather than raising, and grouping then
    # yields an empty table. That reads as "nothing to report" when the truth
    # is the opposite - a constant score is the worst calibration there is, and
    # it has to stay visible.
    try:
        banded = pd.qcut(frame["probability"], bins, duplicates="drop")
    except (ValueError, IndexError):
        banded = None
    frame["band"] = 0 if banded is None or banded.isna().all() else banded

    table = (frame.groupby("band", observed=True)
             .agg(schools=("truth", "size"),
                  predicted=("probability", "mean"),
                  actual=("truth", "mean")))
    table["gap"] = table["actual"] - table["predicted"]
    return table.round(4)


def ks(truth, probability):
    """Largest gap between the two score distributions."""
    order = np.argsort(np.asarray(probability))
    t = np.asarray(truth).astype(int)[order]
    positives = np.cumsum(t) / max(t.sum(), 1)
    negatives = np.cumsum(1 - t) / max((1 - t).sum(), 1)
    return float(np.max(np.abs(positives - negatives)))


def report(truth, probability, threshold, name="model"):
    """Print the whole picture and return it."""
    from sklearn.metrics import roc_auc_score

    auc = roc_auc_score(truth, probability)
    metrics = at_threshold(truth, probability, threshold)
    metrics.update({"auc": round(auc, 4), "gini": round(2 * auc - 1, 4),
                    "ks": round(ks(truth, probability), 4)})

    print(f"\n{'=' * 64}\n{name.upper()}\n{'=' * 64}")
    print(f"  AUC {metrics['auc']}   Gini {metrics['gini']}   KS {metrics['ks']}")

    print("\nCONFUSION MATRIX")
    print(confusion_frame(truth, (np.asarray(probability) >= threshold)).to_string())

    print("\nAT THE CHOSEN CUT")
    for key in ("threshold", "flagged", "flagged_share", "precision", "recall",
                "specificity", "f1", "f2", "accuracy", "balanced_accuracy",
                "youden_j"):
        print(f"  {key:<20} {metrics[key]}")

    print("\nDECILES (1 = highest risk)")
    print(deciles(truth, probability).to_string())

    print("\nCALIBRATION")
    print(calibration(truth, probability).to_string())

    return metrics
