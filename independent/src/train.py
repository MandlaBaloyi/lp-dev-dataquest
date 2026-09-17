"""Stage 3 - WoE scorecard, tree benchmark, evaluation and the 2025 ranking.

    python -m independent.src.train

Bins are fitted on the training years only and applied unchanged to
validation, test and the 2025 scoring year. The decision threshold is chosen on
validation and applied unchanged to test.
"""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score, recall_score,
                             roc_auc_score, roc_curve)

from independent.src import woe
from independent.src.features import CATEGORICAL, MIN_LEARNERS, NUMERIC
from independent.src.paths import CLEAN_PANEL, MODEL_FRAME, out

# years_observed only counts years since 2007, so it tracks the calendar year
# and drifts between train and test. closing_flag has 15 rows, none labelled.
NUM = [c for c in NUMERIC if c != "years_observed"]
CAT = [c for c in CATEGORICAL if c != "closing_flag"]

MIN_IV = 0.02
MAX_CORR = 0.7
TARGET_RECALL = 0.70
PDO, BASE_SCORE, BASE_ODDS = 20, 600, 50
FACTOR = PDO / np.log(2)
OFFSET = BASE_SCORE - FACTOR * np.log(BASE_ODDS)
SEED = 7

LABELS = {
    "log_learners": "school size (learners)",
    "ler": "learners per educator",
    "chg1": "enrolment change over the last year",
    "chg1_rel_prov": "last-year enrolment change vs province",
    "chg3": "enrolment trend over three years",
    "vol": "enrolment volatility",
    "peak_ratio": "enrolment as a share of the school's own peak",
    "edu_chg1": "educator change over the last year",
    "district_chg1": "district's typical enrolment change",
    "district_schools": "number of FET schools in the district",
    "nearby_5km": "FET schools within 5 km",
    "nearby_10km": "FET schools within 10 km",
    "nearby_chg1": "enrolment change at schools within 10 km",
    "size_vs_nearby": "size relative to schools within 10 km",
    "quintile": "poverty quintile",
    "province": "province",
    "sector": "public / independent",
    "phase": "secondary / combined",
    "nofee": "fee status",
    "urbanrural": "urban / rural",
}


# ---------------------------------------------------------------- selection

def select_features(woe_train, y, iv):
    """IV floor, then drop the weaker of any highly correlated pair, then drop
    any feature whose coefficient takes the wrong sign (a sign flip means the
    variable is only correcting another one, which a reader cannot interpret)."""
    log = []
    cand = [c for c in iv.index if iv[c] >= MIN_IV]
    for c in iv.index:
        if iv[c] < MIN_IV:
            log.append((c, f"IV {iv[c]:.3f} below {MIN_IV}"))

    corr = woe_train[cand].corr().abs()
    kept = []
    for c in cand:  # already in descending IV order
        clash = [k for k in kept if corr.loc[c, k] > MAX_CORR]
        if clash:
            log.append((c, f"correlated {corr.loc[c, clash[0]]:.2f} with {clash[0]} (higher IV)"))
        else:
            kept.append(c)

    while True:
        lr = fit_lr(woe_train[kept], y)
        coef = pd.Series(lr.coef_[0], index=kept)
        wrong = coef[coef > 0]
        if wrong.empty:
            break
        drop = wrong.idxmax()
        log.append((drop, f"coefficient sign reversed ({wrong[drop]:+.3f}) once other variables present"))
        kept.remove(drop)
    return kept, lr, log


def fit_lr(X, y):
    return LogisticRegression(C=1.0, max_iter=2000).fit(X, y)


# ---------------------------------------------------------------- scorecard

def scorecard_table(bins, lr, feats):
    n = len(feats)
    b0 = lr.intercept_[0]
    rows = []
    for c, beta in zip(feats, lr.coef_[0]):
        t = bins[c].table.copy()
        t["_o"] = t.bin.map(bin_order)
        t = t.sort_values("_o").drop(columns="_o")
        t["points"] = (-FACTOR * beta * t.woe + (OFFSET - FACTOR * b0) / n).round(1)
        t.insert(0, "feature", c)
        t.insert(1, "description", LABELS[c])
        t["coefficient"] = beta
        rows.append(t)
    return pd.concat(rows, ignore_index=True)


def bin_order(lab):
    if lab == woe.MISSING:
        return np.inf
    if lab.startswith("["):
        return float(lab.strip("[)").split(", ")[0])
    return 0.0


def points(frame, bins, lr, feats):
    n = len(feats)
    b0 = lr.intercept_[0]
    X = woe.transform(frame[feats], {c: bins[c] for c in feats})
    return -FACTOR * X * lr.coef_[0] + (OFFSET - FACTOR * b0) / n


def reasons(frame, pts, bins, card, k=3):
    """The k features costing the school the most points relative to the best
    bin of that feature - the standard adverse-reason construction."""
    best = card.groupby("feature").points.max()
    shortfall = best[pts.columns] - pts
    out_rows = []
    for idx, row in shortfall.iterrows():
        top = row.sort_values(ascending=False).head(k)
        texts = []
        for c, gap in top.items():
            if gap <= 0.5:
                continue
            lab = bins[c].labels(frame.loc[[idx], c]).iat[0]
            if lab == woe.MISSING:
                texts.append(f"{describe_bin(c, lab)} (-{gap:.0f} pts)")
            else:
                texts.append(f"{LABELS[c]}: {describe_bin(c, lab)} (-{gap:.0f} pts)")
        out_rows.append(texts + [""] * (k - len(texts)))
    return pd.DataFrame(out_rows, index=frame.index, columns=[f"reason_{i + 1}" for i in range(k)])


MISSING_TEXT = {
    "vol": "fewer than four years of history",
    "chg3": "fewer than three years of history",
    "chg1": "no enrolment for the previous year",
    "nearby_10km": "no location on record",
    "nearby_5km": "no location on record",
    "nearby_chg1": "no location on record",
    "size_vs_nearby": "no location on record",
    "edu_chg1": "educator count not published",
    "ler": "educator count not published",
    "quintile": "quintile never published",
}


def describe_bin(c, lab):
    if lab == woe.MISSING:
        return MISSING_TEXT.get(c, "not published")
    if not lab.startswith("["):
        return lab
    lo, hi = lab.strip("[)").split(", ")
    pct = c in {"chg1", "chg1_rel_prov", "chg3", "edu_chg1", "district_chg1", "nearby_chg1"}
    share = c == "peak_ratio"

    def fmt(v):
        v = float(v)
        if np.isinf(v):
            return None
        if pct:
            return f"{v * 100:+.1f}%"
        if share:
            return f"{v * 100:.0f}%"
        if c == "log_learners":
            return f"{np.expm1(v):.0f}"
        return f"{v:.2f}".rstrip("0").rstrip(".")

    if c == "quintile":
        a = 1 if np.isinf(float(lo)) else int(float(lo))
        b = 5 if np.isinf(float(hi)) else int(float(hi)) - 1
        return f"Q{a}" if a == b else f"Q{a}-Q{b}"
    a, b = fmt(lo), fmt(hi)
    if a is None:
        return f"below {b}"
    if b is None:
        return f"{a} or more"
    return f"{a} to {b}"


# ---------------------------------------------------------------- metrics

def metrics(y, p, threshold):
    pred = (p >= threshold).astype(int)
    auc = roc_auc_score(y, p)
    top = p >= np.quantile(p, 0.9)
    return {
        "n": int(len(y)),
        "event_rate": float(y.mean()),
        "auc": auc,
        "gini": 2 * auc - 1,
        "ks": ks_stat(y, p),
        "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred),
        "f1": f1_score(y, pred),
        "accuracy": accuracy_score(y, pred),
        "accuracy_all_negative": float(1 - y.mean()),
        "flagged_share": float(pred.mean()),
        "top10_precision": float(y[top].mean()),
        "top10_recall": float(y[top].sum() / y.sum()),
        "top10_lift": float(y[top].mean() / y.mean()),
    }


def ks_stat(y, p):
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def threshold_for_recall(y, p, target):
    """Highest threshold that still catches `target` of the at-risk schools."""
    order = np.sort(p)[::-1]
    ys = np.asarray(y)[np.argsort(p)[::-1]]
    caught = np.cumsum(ys) / ys.sum()
    i = int(np.argmax(caught >= target))
    return float(order[i])


def psi(expected, actual, bins=10):
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, 1e-6, None), np.clip(a, 1e-6, None)
    return float(np.sum((a - e) * np.log(a / e)))


# ---------------------------------------------------------------- benchmark

def tree_matrix(frame, cats):
    X = frame[NUM].copy()
    for c in CAT:
        X[c] = pd.Categorical(frame[c].astype("string"), categories=cats[c]).codes.astype(float)
        X.loc[X[c] < 0, c] = np.nan
    return X


def fit_tree(X, y):
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=100,
        l2_regularization=1.0, categorical_features=[X.columns.get_loc(c) for c in CAT],
        early_stopping=False, random_state=SEED,
    ).fit(X, y)


# ---------------------------------------------------------------- leakage checks

def leakage_checks(lab, feats_all, test):
    """Quantify the two silent mistakes named in the brief, on this data."""
    res = {}
    rng = np.random.default_rng(SEED)

    # 1. Random row split across all labelled years vs the year split.
    pool = lab[lab.split.isin(["train", "valid", "test"])]
    is_train = rng.random(len(pool)) < 0.7
    tr, te = pool[is_train], pool[~is_train]
    b = woe.fit(tr, tr.loss, NUM, CAT)
    lr = fit_lr(woe.transform(tr[feats_all], {c: b[c] for c in feats_all}), tr.loss)
    p = lr.predict_proba(woe.transform(te[feats_all], {c: b[c] for c in feats_all}))[:, 1]
    res["scorecard_random_split_auc"] = roc_auc_score(te.loss, p)
    cats = {c: sorted(tr[c].dropna().astype(str).unique()) for c in CAT}
    Xtr, Xte = tree_matrix(tr, cats), tree_matrix(te, cats)
    # The tree gets the school's location, which is how it can recognise a
    # school it has already seen in another year.
    Xtr["lat_"], Xtr["lon_"] = tr.lat.to_numpy(), tr.lon.to_numpy()
    Xte["lat_"], Xte["lon_"] = te.lat.to_numpy(), te.lon.to_numpy()
    t = fit_tree(Xtr, tr.loss)
    res["tree_with_location_random_split_auc"] = roc_auc_score(te.loss, t.predict_proba(Xte)[:, 1])

    train = lab[lab.split == "train"]
    Xtr, Xte = tree_matrix(train, cats), tree_matrix(test, cats)
    Xtr["lat_"], Xtr["lon_"] = train.lat.to_numpy(), train.lon.to_numpy()
    Xte["lat_"], Xte["lon_"] = test.lat.to_numpy(), test.lon.to_numpy()
    t = fit_tree(Xtr, train.loss)
    res["tree_with_location_year_split_auc"] = roc_auc_score(test.loss, t.predict_proba(Xte)[:, 1])

    # 2. Bins fitted on train+valid+test, model trained on train, scored on test.
    b_all = woe.fit(pool, pool.loss, NUM, CAT)
    lr = fit_lr(woe.transform(train[feats_all], {c: b_all[c] for c in feats_all}), train.loss)
    p = lr.predict_proba(woe.transform(test[feats_all], {c: b_all[c] for c in feats_all}))[:, 1]
    res["scorecard_bins_fitted_on_all_data_test_auc"] = roc_auc_score(test.loss, p)
    return res


# ---------------------------------------------------------------- main

def main():
    df = pd.read_csv(MODEL_FRAME)
    geo = pd.read_csv(CLEAN_PANEL, usecols=["emis", "lat", "lon"]).drop_duplicates("emis")
    df = df.merge(geo, on="emis", how="left")
    lab = df[df.loss.notna()].copy()
    train, valid, test = (lab[lab.split == s] for s in ("train", "valid", "test"))

    # --- bins and IV, training years only
    bins = woe.fit(train, train.loss, NUM, CAT)
    iv = woe.information_value(bins)
    iv_valid = pd.Series({c: woe.woe_table(bins[c].labels(valid[c]), valid.loss).iv.sum() for c in bins})
    Wtr = woe.transform(train, bins)

    feats, lr, sel_log = select_features(Wtr, train.loss, iv)

    iv_df = pd.DataFrame({"feature": iv.index, "description": [LABELS[c] for c in iv.index],
                          "iv_train": iv.values.round(4), "iv_valid": iv_valid[iv.index].values.round(4),
                          "band": [woe.iv_band(v) for v in iv.values],
                          "in_model": [c in feats for c in iv.index]})
    reason_map = dict(sel_log)
    iv_df["selection_note"] = iv_df.feature.map(reason_map).fillna("kept")
    iv_df.to_csv(out("iv.csv"), index=False)

    card = scorecard_table(bins, lr, feats)
    card.to_csv(out("scorecard.csv"), index=False)

    def score_frame(frame):
        pts = points(frame, bins, lr, feats)
        return pts, pts.sum(axis=1)

    def prob(frame):
        return lr.predict_proba(woe.transform(frame[feats], {c: bins[c] for c in feats}))[:, 1]

    p = {s: prob(f) for s, f in (("train", train), ("valid", valid), ("test", test))}
    thr = threshold_for_recall(valid.loss, p["valid"], TARGET_RECALL)

    # --- benchmark
    cats = {c: sorted(train[c].dropna().astype(str).unique()) for c in CAT}
    tree = fit_tree(tree_matrix(train, cats), train.loss)
    pt = {s: tree.predict_proba(tree_matrix(f, cats))[:, 1]
          for s, f in (("train", train), ("valid", valid), ("test", test))}
    thr_tree = threshold_for_recall(valid.loss, pt["valid"], TARGET_RECALL)

    results = {}
    for s, f in (("train", train), ("valid", valid), ("test", test)):
        results[f"scorecard_{s}"] = metrics(f.loss.to_numpy(), p[s], thr)
        results[f"tree_{s}"] = metrics(f.loss.to_numpy(), pt[s], thr_tree)
    table = pd.DataFrame(results).T
    table.to_csv(out("metrics.csv"))

    # by-year stability on test
    by_year = []
    for (s, y), f in lab[lab.split.isin(["valid", "test"])].groupby(["split", "year"]):
        by_year.append({"split": s, "year": y, "n": len(f), "event_rate": f.loss.mean(),
                        "scorecard_auc": roc_auc_score(f.loss, prob(f)),
                        "tree_auc": roc_auc_score(f.loss, tree.predict_proba(tree_matrix(f, cats))[:, 1])})
    pd.DataFrame(by_year).to_csv(out("auc_by_year.csv"), index=False)

    _, s_train = score_frame(train)
    _, s_test = score_frame(test)
    score_rows = df[(df.split == "score") & (df.learners >= MIN_LEARNERS)].copy()
    pts_score, s_score = score_frame(score_rows)

    leak = leakage_checks(lab, feats, test)

    summary = {
        "features_in_model": feats,
        "coefficients": dict(zip(feats, lr.coef_[0].round(4).tolist())),
        "intercept": float(lr.intercept_[0]),
        "threshold_scorecard_prob": thr,
        "threshold_tree_prob": thr_tree,
        "target_recall_on_valid": TARGET_RECALL,
        "psi_score_train_vs_test": psi(s_train.to_numpy(), s_test.to_numpy()),
        "psi_score_train_vs_2025": psi(s_train.to_numpy(), s_score.to_numpy()),
        "leakage_checks": leak,
        "metrics": {k: {m: (round(v, 4) if isinstance(v, float) else v) for m, v in d.items()}
                    for k, d in results.items()},
        "scaling": {"pdo": PDO, "base_score": BASE_SCORE, "base_odds_good_to_bad": BASE_ODDS},
        "bins": {c: {"kind": bins[c].kind, "edges": bins[c].edges, "categories": bins[c].categories,
                     "woe": bins[c].table.set_index("bin").woe.round(4).to_dict()} for c in feats},
    }
    with open(out("model.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=float)

    # --- 2025 ranking
    score_rows["score"] = s_score.round(0).astype(int)
    score_rows["p_loss"] = prob(score_rows).round(4)
    # Two tiers: the worst tenth is a list a province can actually visit; the
    # validation threshold marks everything the model expects to catch 70% of
    # losses within.
    priority = score_rows.score <= np.quantile(score_rows.score, 0.10)
    score_rows["tier"] = np.select([priority, score_rows.p_loss >= thr], ["PRIORITY", "WATCH"], "")
    score_rows = pd.concat([score_rows, reasons(score_rows, pts_score, bins, card)], axis=1)
    score_rows = score_rows.sort_values("score").reset_index(drop=True)
    score_rows.insert(0, "rank", np.arange(1, len(score_rows) + 1))
    cols = ["rank", "emis", "school", "province", "district", "phase", "sector", "quintile",
            "learners", "score", "p_loss", "tier", "reason_1", "reason_2", "reason_3"]
    score_rows[cols].to_csv(out("ranking_2025.csv"), index=False)

    # validation/test scored rows kept for the report's charts
    test_out = test[["emis", "year", "province", "loss"]].assign(score=s_test.values, p=p["test"], p_tree=pt["test"])
    test_out.to_csv(out("test_scores.csv"), index=False)

    pd.set_option("display.width", 200)
    print(iv_df.to_string())
    print(table[["n", "event_rate", "auc", "gini", "ks", "precision", "recall", "f1", "accuracy",
                 "top10_precision", "top10_lift"]].round(3).to_string())
    print(json.dumps({k: summary[k] for k in ("features_in_model", "threshold_scorecard_prob",
                                               "psi_score_train_vs_test", "psi_score_train_vs_2025",
                                               "leakage_checks")}, indent=2, default=float))
    print(score_rows[cols].head(10).to_string())


if __name__ == "__main__":
    main()
