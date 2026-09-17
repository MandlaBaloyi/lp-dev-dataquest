"""Weight of Evidence binning, fitted once on training rows and then frozen.

Convention: WoE = ln(share of non-events / share of events). A positive WoE is
a safer-than-average bin. Missing values always get their own bin, because in
this data missingness is itself informative (e.g. a quintile never published).

Bins are not forced to be monotonic. Enrolment change has a genuine U-shape -
schools with a sudden jump are as likely to lose learners as schools already
shrinking - and forcing monotonicity would erase it.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MISSING = "MISSING"
OTHER = "OTHER"
SMOOTH = 0.5
# A missing bin this small has too little evidence to carry its own weight;
# it is scored as average (WoE 0) instead.
MIN_MISSING_SHARE = 0.01


@dataclass
class Binner:
    name: str
    kind: str                      # "numeric" or "categorical"
    edges: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    table: pd.DataFrame = None

    def labels(self, x):
        if self.kind == "numeric":
            x = pd.to_numeric(x, errors="coerce")
            cut = pd.cut(x, [-np.inf] + self.edges + [np.inf], right=False)
            lab = cut.astype("string")
        else:
            lab = x.astype("string")
            lab = lab.where(lab.isin(self.categories) | lab.isna(), OTHER)
        return lab.fillna(MISSING)

    def transform(self, x):
        woe = self.table.set_index("bin").woe
        lab = self.labels(x)
        # A bin unseen in training (e.g. a new category) is neutral.
        return lab.map(woe).fillna(0.0).astype(float)


def woe_table(lab, y):
    t = pd.DataFrame({"bin": lab.values, "y": y.values}).groupby("bin", sort=False).y.agg(["size", "sum"])
    t.columns = ["n", "events"]
    t["non_events"] = t.n - t.events
    ev, ne = t.events.sum(), t.non_events.sum()
    t["event_rate"] = t.events / t.n
    p_ne = (t.non_events + SMOOTH) / (ne + SMOOTH * len(t))
    p_ev = (t.events + SMOOTH) / (ev + SMOOTH * len(t))
    t["woe"] = np.log(p_ne / p_ev)
    t["iv"] = (p_ne - p_ev) * t.woe
    return t.reset_index()


def neutralise_small_missing(t):
    small = (t.bin == MISSING) & (t.n / t.n.sum() < MIN_MISSING_SHARE)
    t.loc[small, ["woe", "iv"]] = 0.0
    return t


def _merge_numeric(x, y, edges, min_share, min_woe_gap):
    """Merge adjacent bins that are too small or not different enough."""
    changed = True
    while changed and edges:
        changed = False
        cut = pd.cut(x, [-np.inf] + edges + [np.inf], right=False)
        t = woe_table(cut.astype("string"), y)
        order = {str(c): i for i, c in enumerate(cut.cat.categories)}
        t = t.assign(o=t.bin.map(order)).sort_values("o").reset_index(drop=True)
        share = t.n / t.n.sum()
        # Smallest bin first, then the pair of neighbours closest in WoE.
        if share.min() < min_share:
            i = int(share.idxmin())
            j = i - 1 if i == len(t) - 1 or (i > 0 and share[i - 1] < share[i + 1]) else i
            del edges[j]
            changed = True
            continue
        gaps = t.woe.diff().abs().iloc[1:]
        if len(gaps) and gaps.min() < min_woe_gap:
            del edges[int(gaps.idxmin()) - 1]
            changed = True
    return edges


def fit_numeric(name, x, y, max_bins=8, min_share=0.05, min_woe_gap=0.05):
    x = pd.to_numeric(x, errors="coerce")
    present = x.notna()
    qs = np.unique(np.nanquantile(x[present], np.linspace(0, 1, max_bins + 1)[1:-1]))
    # An edge at the minimum would leave the first bin empty.
    qs = qs[qs > x[present].min()]
    edges = _merge_numeric(x[present], y[present], list(qs), min_share, min_woe_gap)
    b = Binner(name, "numeric", edges=[float(e) for e in edges])
    b.table = neutralise_small_missing(woe_table(b.labels(x), y))
    return b


def fit_categorical(name, x, y, min_share=0.02):
    lab = x.astype("string")
    share = lab.value_counts(normalize=True)
    keep = share[share >= min_share].index.tolist()
    b = Binner(name, "categorical", categories=keep)
    b.table = neutralise_small_missing(woe_table(b.labels(x), y))
    return b


def fit(frame, y, numeric, categorical):
    """Fit one binner per feature. Pass training rows only."""
    bins = {}
    for c in numeric:
        bins[c] = fit_numeric(c, frame[c], y)
    for c in categorical:
        bins[c] = fit_categorical(c, frame[c], y)
    return bins


def transform(frame, bins):
    return pd.DataFrame({c: b.transform(frame[c]) for c, b in bins.items()}, index=frame.index)


def information_value(bins):
    return pd.Series({c: b.table.iv.sum() for c, b in bins.items()}).sort_values(ascending=False)


def iv_band(iv):
    if iv < 0.02:
        return "not useful"
    if iv < 0.1:
        return "weak"
    if iv < 0.3:
        return "medium"
    if iv < 0.5:
        return "strong"
    return "suspicious"
