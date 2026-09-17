"""Stage 2 - cleaned panel into a model frame: one row per school per year,
features known at that year, and the outcome two years later.

    python -m independent.src.features

Target (see REPORT.md for why):
    loss = 1 when a school's enrolment change from year t to t+2 is at least
    15 percentage points worse than the median change of in-scope schools in
    its province over the same window.

Every feature for year t uses only rows from years <= t.
"""
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from independent.src.paths import CLEAN_PANEL, MODEL_FRAME

HORIZON = 2
EXCESS_LOSS = -0.15
MIN_LEARNERS = 100
EARTH_KM = 6371.0

SPLITS = {
    # Outcomes for the last training year are observed in 2018, before the
    # first validation year. Validation outcomes are observed by 2021, the
    # first test year. 2015 has no label (its t+2 is the dropped 2017) and
    # 2020 is left out so that no validation outcome postdates a test feature.
    "train": range(2008, 2017),
    "valid": (2018, 2019),
    "test": (2021, 2022, 2023),
    "score": (2025,),
}

NUMERIC = ["log_learners", "ler", "chg1", "chg1_rel_prov", "chg3", "vol", "peak_ratio",
           "edu_chg1", "years_observed", "district_chg1", "district_schools",
           "nearby_5km", "nearby_10km", "nearby_chg1", "size_vs_nearby", "quintile"]
CATEGORICAL = ["province", "sector", "phase", "nofee", "urbanrural", "closing_flag"]


def value_at(wide, years, offsets):
    """For each row, the value at the first of year-k (k in offsets) that exists.
    Returns the value and the gap in years it was found at."""
    val = pd.Series(np.nan, index=years.index)
    gap = pd.Series(np.nan, index=years.index)
    lookup = wide.stack()
    for k in offsets:
        key = pd.MultiIndex.from_arrays([years.index.get_level_values("emis"), years.values - k])
        v = lookup.reindex(key).to_numpy()
        take = val.isna().to_numpy() & ~np.isnan(v)
        val[take] = v[take]
        gap[take] = k
    return val, gap


def annualised(now, then, gap):
    return (now / then) ** (1 / gap) - 1


def lagged(df, col, offsets):
    wide = df.pivot(index="emis", columns="year", values=col)
    idx = df.set_index(["emis", "year"]).index
    years = pd.Series(idx.get_level_values("year"), index=idx)
    val, gap = value_at(wide, years, offsets)
    return val.to_numpy(), gap.to_numpy()


def school_history(df):
    df = df.sort_values(["emis", "year"]).copy()
    L = df.learners

    prev, gap = lagged(df, "learners", [1, 2])
    df["chg1"] = annualised(L.to_numpy(), prev, gap)
    prev3, gap3 = lagged(df, "learners", [3, 4])
    df["chg3"] = annualised(L.to_numpy(), prev3, gap3)
    e_prev, e_gap = lagged(df, "educators", [1, 2])
    df["edu_chg1"] = annualised(df.educators.to_numpy(), e_prev, e_gap)

    df["log_learners"] = np.log1p(L)
    df["ler"] = L / df.educators

    g = df.groupby("emis")
    logL = np.log(L)
    step = logL - g["learners"].shift().pipe(np.log)
    df["vol"] = step.groupby(df.emis).transform(lambda s: s.rolling(5, min_periods=3).std())
    df["peak_ratio"] = L / g["learners"].cummax()
    df["years_observed"] = g.cumcount() + 1
    return df


def context(df):
    """Features describing a school's surroundings in the same year."""
    grp = df.groupby(["province", "year"]).chg1
    df["chg1_rel_prov"] = df.chg1 - grp.transform("median")
    d = df.groupby(["district_key", "year"])
    df["district_chg1"] = d.chg1.transform("median")
    df["district_schools"] = d.emis.transform("size")

    for col in ["nearby_5km", "nearby_10km", "nearby_chg1", "size_vs_nearby"]:
        df[col] = np.nan
    for year, part in df[df.lat.notna() & df.learners.notna()].groupby("year"):
        coords = np.radians(part[["lat", "lon"]].to_numpy())
        tree = BallTree(coords, metric="haversine")
        n5 = tree.query_radius(coords, r=5 / EARTH_KM, count_only=True) - 1
        ind10 = tree.query_radius(coords, r=10 / EARTH_KM)
        chg = part.chg1.to_numpy()
        size = part.learners.to_numpy()
        n10 = np.empty(len(part))
        near_chg = np.full(len(part), np.nan)
        rel_size = np.full(len(part), np.nan)
        for i, nb in enumerate(ind10):
            nb = nb[nb != i]
            n10[i] = len(nb)
            if len(nb):
                c = chg[nb]
                c = c[~np.isnan(c)]
                if len(c):
                    near_chg[i] = np.median(c)
                rel_size[i] = size[i] / np.median(size[nb])
        df.loc[part.index, "nearby_5km"] = n5
        df.loc[part.index, "nearby_10km"] = n10
        df.loc[part.index, "nearby_chg1"] = near_chg
        df.loc[part.index, "size_vs_nearby"] = rel_size
    return df


def outcome(df):
    wide = df.pivot(index="emis", columns="year", values="learners")
    idx = df.set_index(["emis", "year"]).index
    future = wide.stack().reindex(
        pd.MultiIndex.from_arrays([idx.get_level_values(0), idx.get_level_values(1) + HORIZON])
    ).to_numpy()
    df["learners_t2"] = future
    df["chg_t2"] = df.learners_t2 / df.learners - 1

    last_seen = df.groupby("emis").year.transform("max")
    df["closed_by_t2"] = (last_seen < df.year + HORIZON) & (df.year + HORIZON <= 2025)

    labelled = df.chg_t2.notna() & (df.learners >= MIN_LEARNERS)
    med = df[labelled].groupby(["province", "year"]).chg_t2.median()
    df["prov_chg_t2"] = df.set_index(["province", "year"]).index.map(med)
    df["excess_chg_t2"] = df.chg_t2 - df.prov_chg_t2
    df["loss"] = np.where(labelled, (df.excess_chg_t2 <= EXCESS_LOSS).astype(float), np.nan)
    return df


def assign_split(year):
    for name, years in SPLITS.items():
        if year in years:
            return name
    return "unused"


def build(clean):
    df = clean.reset_index(drop=True)
    df = school_history(df)
    df = context(df)
    df = outcome(df)
    df["split"] = df.year.map(assign_split)
    df["nofee"] = df.nofee.map({1.0: "NO_FEE", 0.0: "FEE"})
    df["closing_flag"] = df.closing_flag.map({1: "CLOSING", 0: "OPEN"})
    return df


def main():
    clean = pd.read_csv(CLEAN_PANEL)
    df = build(clean)
    keep = (["emis", "year", "split", "school", "district", "district_key", "learners",
             "educators", "learners_t2", "chg_t2", "prov_chg_t2", "excess_chg_t2",
             "closed_by_t2", "loss"] + NUMERIC + [c for c in CATEGORICAL if c not in NUMERIC])
    df = df[keep]
    df.to_csv(MODEL_FRAME, index=False, compression="gzip")

    lab = df[df.loss.notna()]
    print(lab.groupby("split").loss.agg(["size", "mean"]))
    print(lab.groupby("year").loss.agg(["size", "mean"]).round(3).to_string())
    print(df[df.split == "score"].shape)


if __name__ == "__main__":
    main()
