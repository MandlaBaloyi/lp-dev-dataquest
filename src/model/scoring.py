"""Score schools from the saved scorecard (outputs/model.json) alone.

train.py writes the frozen bins, WoE values and coefficients to model.json;
this module rebuilds the scorecard from that file, so the app and anyone
downstream score exactly as the evaluated model did without re-training.
"""
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.eda import woe
from src.common.paths import out


@dataclass
class Scorecard:
    features: list
    bins: dict
    coef: dict
    intercept: float
    factor: float
    offset: float
    threshold: float

    @classmethod
    def load(cls, path=None):
        with open(path or out("model.json")) as fh:
            m = json.load(fh)
        bins = {}
        for c, spec in m["bins"].items():
            b = woe.Binner(c, spec["kind"], edges=spec["edges"], categories=spec["categories"])
            b.table = pd.DataFrame({"bin": list(spec["woe"]), "woe": list(spec["woe"].values())})
            bins[c] = b
        s = m["scaling"]
        factor = s["pdo"] / np.log(2)
        offset = s["base_score"] - factor * np.log(s["base_odds_good_to_bad"])
        return cls(m["features_in_model"], bins, m["coefficients"], m["intercept"],
                   factor, offset, m["threshold_scorecard_prob"])

    def _share(self):
        return (self.offset - self.factor * self.intercept) / len(self.features)

    def points(self, frame):
        """Points per feature, one column per feature. Higher = safer."""
        cols = {}
        for c in self.features:
            w = self.bins[c].transform(frame[c])
            cols[c] = -self.factor * self.coef[c] * w + self._share()
        return pd.DataFrame(cols, index=frame.index)

    def score(self, frame):
        return self.points(frame).sum(axis=1)

    def probability(self, frame):
        """P(loss). The score is a linear transform of the log-odds."""
        log_odds_good = (self.score(frame) - self.offset) / self.factor
        return 1 / (1 + np.exp(log_odds_good))

    def table(self):
        """Every bin of every feature with its points, in natural bin order."""
        rows = []
        for c in self.features:
            t = self.bins[c].table.copy()
            t["points"] = -self.factor * self.coef[c] * t.woe + self._share()
            t["feature"] = c
            t["order"] = t.bin.map(_order)
            rows.append(t.sort_values("order"))
        return pd.concat(rows, ignore_index=True)

    def best_points(self):
        return self.table().groupby("feature").points.max()


def _order(lab):
    if lab == woe.MISSING:
        return np.inf
    if lab.startswith("["):
        return float(lab.strip("[)").split(", ")[0])
    return 0.0
