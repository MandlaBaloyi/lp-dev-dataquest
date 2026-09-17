"""Weight of Evidence and Information Value.

Standard credit-scorecard tooling, applied here to school risk. For each bin of
a variable:

    WoE = ln( share of good in this bin / share of bad in this bin )
     IV = sum over bins of ( share_good - share_bad ) * WoE

WoE says which direction a bin pushes and how hard. IV scores the whole
variable in one number, so variables can be ranked before any model is fitted.

Two properties make WoE worth the trouble on data this messy. Missing is just
another bin, so "TO BE UPDATED" on 39,923 rows gets a weight instead of
forcing a choice between dropping the rows and inventing a value. And a
category with 200 levels becomes one numeric column rather than 200 dummies.

THE TRAP, and it is the one that quietly ruins scorecards:

    Bins must be fitted on training data only.

Fit them on everything and every bin has seen the test set. AUC comes back
inflated, nothing errors, and the model underperforms the moment it meets data
it has not seen. Hence fit() and transform() are separate, exactly as
scikit-learn separates them, so applying training bins to test data is the
path of least resistance.
"""
import numpy as np
import pandas as pd

# Keeps the logarithm finite when a bin holds only one class.
EPSILON = 0.5

# Conventional reading of IV in credit scoring. Above 0.5 is worth a second
# look rather than celebration - it often means the variable encodes the
# target rather than predicting it.
IV_BANDS = [
    (0.02, "unpredictive"),
    (0.10, "weak"),
    (0.30, "medium"),
    (0.50, "strong"),
    (float("inf"), "suspiciously strong - check for leakage"),
]


def iv_strength(value):
    for threshold, label in IV_BANDS:
        if value < threshold:
            return label
    return IV_BANDS[-1][1]


def bin_numeric(series, bins=10):
    """Cut a numeric variable into quantile bins, tolerating ties.

    Quantiles rather than equal width: school enrolment is heavily skewed, and
    equal-width bins would put almost every school in the first bucket.
    """
    series = pd.to_numeric(series, errors="coerce")
    try:
        return pd.qcut(series, q=bins, duplicates="drop")
    except (ValueError, IndexError):
        return pd.cut(series, bins=min(bins, max(series.nunique(), 1)))


def woe_table(feature, target, bins=10, numeric=None):
    """WoE and IV per bin for one variable.

    target must be binary, 1 = the event being modelled (a high-risk school).
    """
    feature = pd.Series(feature).reset_index(drop=True)
    target = pd.Series(target).reset_index(drop=True).astype(float)

    if numeric is None:
        numeric = pd.api.types.is_numeric_dtype(feature) and feature.nunique() > 12

    binned = bin_numeric(feature, bins) if numeric else feature.astype("string").fillna("UNKNOWN")

    frame = pd.DataFrame({"bin": binned.astype("string"), "target": target}).dropna(subset=["target"])
    frame["bin"] = frame["bin"].fillna("UNKNOWN")

    grouped = frame.groupby("bin", dropna=False)["target"].agg(rows="count", bad="sum")
    grouped["good"] = grouped["rows"] - grouped["bad"]

    total_bad = max(grouped["bad"].sum(), EPSILON)
    total_good = max(grouped["good"].sum(), EPSILON)

    grouped["bad_rate"] = grouped["bad"] / grouped["rows"]
    grouped["dist_bad"] = (grouped["bad"] + EPSILON) / (total_bad + EPSILON * len(grouped))
    grouped["dist_good"] = (grouped["good"] + EPSILON) / (total_good + EPSILON * len(grouped))
    grouped["woe"] = np.log(grouped["dist_good"] / grouped["dist_bad"])
    grouped["iv_contribution"] = (grouped["dist_good"] - grouped["dist_bad"]) * grouped["woe"]

    return grouped.reset_index().sort_values("bin")


def information_value(feature, target, bins=10, numeric=None):
    """Total IV for one variable."""
    table = woe_table(feature, target, bins=bins, numeric=numeric)
    return float(table["iv_contribution"].sum())


def rank_by_iv(frame, target, features=None, bins=10):
    """IV for every candidate feature, strongest first.

    This is the table that decides what enters the model, and it is the one
    slide that shows an EDA actually informed the modelling rather than
    decorating it.
    """
    target = pd.Series(target).reset_index(drop=True)
    features = features or [c for c in frame.columns if frame[c].notna().any()]

    rows = []
    for column in features:
        try:
            value = information_value(frame[column], target, bins=bins)
        except Exception as exc:                      # a column that cannot bin
            rows.append({"feature": column, "iv": float("nan"),
                         "strength": f"could not compute: {type(exc).__name__}"})
            continue
        rows.append({"feature": column, "iv": round(value, 4),
                     "strength": iv_strength(value)})

    return pd.DataFrame(rows).sort_values("iv", ascending=False, na_position="last")


class WoEEncoder:
    """Fit WoE bins on training data, apply them to test data.

    Separate fit and transform is not ceremony here. It is the whole defence
    against the leakage described at the top of this module.
    """

    def __init__(self, bins=10):
        self.bins = bins
        self.maps_ = {}
        self.default_ = {}

    def fit(self, frame, target, features=None):
        features = features or list(frame.columns)
        for column in features:
            table = woe_table(frame[column], target, bins=self.bins)
            self.maps_[column] = dict(zip(table["bin"], table["woe"]))
            self.default_[column] = 0.0        # unseen category: neutral weight
        return self

    def transform(self, frame):
        out = pd.DataFrame(index=frame.index)
        for column, mapping in self.maps_.items():
            if column not in frame.columns:
                continue
            numeric = (pd.api.types.is_numeric_dtype(frame[column])
                       and frame[column].nunique() > 12)
            binned = (bin_numeric(frame[column], self.bins) if numeric
                      else frame[column].astype("string").fillna("UNKNOWN"))
            out[f"woe_{column}"] = (binned.astype("string")
                                    .map(mapping).fillna(self.default_[column]))
        return out

    def fit_transform(self, frame, target, features=None):
        return self.fit(frame, target, features).transform(frame)
