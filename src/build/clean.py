"""Stage 1 - raw school-year panel into a cleaned panel.

Reads only datasets/processed/school_year_panel.csv.gz. Every rule below is
numbered to match independent/DECISIONS.md, and the row counts each rule
touches are written to outputs/cleaning_log.json so the decisions record can
quote real numbers rather than estimates.

    python -m src.clean
"""
import json

import numpy as np
import pandas as pd

from src.common.paths import CLEAN_PANEL, RAW_PANEL, out

# Mainland South Africa's bounding box, with a small margin.
LAT_RANGE = (-35.0, -22.0)
LON_RANGE = (16.0, 33.0)

log = {}


def note(key, n):
    log[key] = int(n)


def to_number(s):
    """Numbers published as text, sometimes with a comma decimal or a dash."""
    s = s.astype("string").str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def norm_text(s):
    return s.astype("string").str.strip().str.upper().str.replace(r"\s+", " ", regex=True)


def ffill_within_school(df, col):
    """Carry the last known value forward only - never backward, which would
    hand a year information published after it."""
    return df.groupby("emis")[col].ffill()


def fix_coordinate(v, lo, hi):
    """Bring a coordinate into range: undo a lost decimal point by dividing by
    powers of ten. Returns NaN if no scaling lands inside the range."""
    if pd.isna(v) or v == 0:
        return np.nan
    for k in range(0, 16):
        x = v / 10 ** k
        if lo <= x <= hi:
            return x
    return np.nan


def clean(df):
    df = df.sort_values(["emis", "year"]).reset_index(drop=True)
    note("rows_in", len(df))

    # D1. The 2017 snapshot is corrupt: national enrolment falls 1.4M and
    # recovers in 2018, with 18-23% of schools in EC and LP moving >30%.
    note("D1_rows_2017_dropped", (df.year == 2017).sum())
    df = df[df.year != 2017].copy()

    # D2. Learner and educator counts: '-' and blanks become missing.
    df["learners"] = to_number(df["learners"])
    df["educators"] = to_number(df["educators"])
    note("D2_learners_missing", df.learners.isna().sum())
    # A school reported open with zero learners is a reporting gap, not a
    # school that lost everyone.
    note("D2_learners_zero_to_missing", (df.learners == 0).sum())
    df.loc[df.learners == 0, "learners"] = np.nan
    note("D2_educators_zero_to_missing", (df.educators == 0).sum())
    df.loc[df.educators == 0, "educators"] = np.nan
    note("D2_educators_missing_2014", df.loc[df.year == 2014, "educators"].isna().sum())

    # D3. Isolated one-year spikes in learners: a value more than 2.5x (or
    # under 0.4x) both neighbours, while the neighbours agree within 25%.
    g = df.groupby("emis")
    prev_l, next_l = g.learners.shift(1), g.learners.shift(-1)
    prev_y, next_y = g.year.shift(1), g.year.shift(-1)
    close = (prev_y >= df.year - 2) & (next_y <= df.year + 2)
    agree = (prev_l / next_l).between(0.75, 1 / 0.75)
    mid = (prev_l + next_l) / 2
    ratio = df.learners / mid
    spike = close & agree & ((ratio > 2.5) | (ratio < 0.4))
    note("D3_learner_spikes_to_missing", spike.sum())
    df.loc[spike, "learners"] = np.nan

    # Learner-educator ratios above 150 are a count in the wrong column.
    ler = df.learners / df.educators
    bad = ler > 150
    note("D2_educators_implausible_ler", bad.sum())
    df.loc[bad, "educators"] = np.nan

    # D4. Coordinates: comma decimals, swapped lat/lon, lost decimal points,
    # zeros. Then one location per school - schools do not move.
    lat, lon = to_number(df["lat"]), to_number(df["lon"])
    swap = (lat > 0) & (lon < 0)
    note("D4_latlon_swapped", swap.sum())
    lat, lon = lat.where(~swap, lon), lon.where(~swap, lat)
    note("D4_coord_zero_or_missing", (lat.isna() | (lat == 0)).sum())
    out_of_range = ~lat.between(*LAT_RANGE) & lat.notna() & (lat != 0)
    note("D4_lat_rescaled_or_dropped", out_of_range.sum())
    lat = lat.map(lambda v: fix_coordinate(v, *LAT_RANGE))
    lon = lon.map(lambda v: fix_coordinate(v, *LON_RANGE))
    df["lat_raw_clean"], df["lon_raw_clean"] = lat, lon
    df["lat"] = df.groupby("emis").lat_raw_clean.transform("median")
    df["lon"] = df.groupby("emis").lon_raw_clean.transform("median")
    note("D4_schools_without_location", df.loc[df.lat.isna(), "emis"].nunique())
    df = df.drop(columns=["lat_raw_clean", "lon_raw_clean"])

    # D5. Categorical spellings.
    status = norm_text(df.status)
    df["closing_flag"] = status.str.contains("CLOS|NOT FUNCTIONAL|NO CURRENT", na=False).astype(int)
    note("D5_rows_flagged_closing", df.closing_flag.sum())
    df["status"] = status

    sector = norm_text(df.sector)
    sector = sector.replace({"INDEPENDENT/PRIVATE": "INDEPENDENT"})
    # 'ORDINARY' is WC 2021 with the type column shifted into sector.
    note("D5_sector_shifted_to_missing", (~sector.isin(["PUBLIC", "INDEPENDENT"]) & sector.notna()).sum())
    sector = sector.where(sector.isin(["PUBLIC", "INDEPENDENT"]))
    df["sector"] = sector
    # Sector does not change year to year; use the school's modal value.
    mode = df.dropna(subset=["sector"]).groupby("emis").sector.agg(lambda s: s.mode().iat[0])
    df["sector"] = df.emis.map(mode)

    phase = norm_text(df.phase).str.split(" ").str[0]
    phase = phase.replace({"SPECIALIZED": "SPECIAL", "HOSPITAL": "SPECIAL", "SCHOOL": "SPECIAL",
                           "PRE-PRIMARY": "OTHER", "ECD": "OTHER", "TO": pd.NA})
    df["phase_year"] = phase
    df["type"] = norm_text(df.type).str.replace(" SCHOOL", "", regex=False)

    q = norm_text(df.quintile).str.replace(r"^N?Q", "", regex=True)
    q = pd.to_numeric(q, errors="coerce")
    q = q.where(q.between(1, 5))
    note("D6_quintile_missing_before_fill", q.isna().sum())
    df["quintile"] = q
    df["quintile"] = ffill_within_school(df, "quintile")
    note("D6_quintile_missing_after_fill", df.quintile.isna().sum())

    nf = norm_text(df.nofee)
    nofee_map = {"YES": 1, "Y": 1, "NO FEE": 1, "NO": 0, "N": 0, "FEE CHARGING": 0, "FEE PAYING": 0}
    # 'FREE CHARGING' (3 rows) could be either a typo of fee charging or a
    # mangled 'no fee'; it is left missing rather than guessed.
    df["nofee"] = nf.map(nofee_map).astype("Float64")
    df["nofee"] = ffill_within_school(df, "nofee")
    note("D6_nofee_missing_after_fill", df.nofee.isna().sum())

    ur = norm_text(df.urbanrural).replace({"DEEP RURAL": "RURAL", "PERI-URBAN": "URBAN"})
    df["urbanrural"] = ur.where(ur.isin(["URBAN", "RURAL"]))
    df["urbanrural"] = ffill_within_school(df, "urbanrural")
    note("D6_urbanrural_missing_after_fill", df.urbanrural.isna().sum())

    # D7. Districts: MP publishes 'NOT APPLICABLE' for 2007-2013, and district
    # names change (renamed municipalities). One stable district per school:
    # its most recent real name.
    d = norm_text(df.district)
    d = d.where(~d.isin(["NOT APPLICABLE", "UNKNOWN"]))
    note("D7_district_not_applicable", (norm_text(df.district) == "NOT APPLICABLE").sum())
    df["district_year"] = d
    latest = df.dropna(subset=["district_year"]).groupby("emis").district_year.last()
    df["district"] = df.emis.map(latest)
    df["district_key"] = df.province + ":" + df.district.fillna("UNKNOWN")
    note("D7_rows_without_district", df.district.isna().sum())

    # D8. Columns not used: circuit (1,781 inconsistent spellings, 17% blank),
    # old/new EMIS (renumbering is handled by leaving vanished schools
    # unlabelled), source file (kept for audit).
    df = df.drop(columns=["circuit"])

    return df


def school_population(df):
    """D9. Which schools teach Grades 10-12.

    Phase is reclassified over time: 1,573 schools labelled COMBINED in 2016
    are PRIMARY by 2023, so COMBINED alone does not mean a school has an FET
    phase. A school is in scope if it is ordinary (not special needs) and
    either labelled SECONDARY in most of its years, or labelled COMBINED in
    most of its years and never PRIMARY.
    """
    ph = df.dropna(subset=["phase_year"]).groupby("emis").phase_year
    share_sec = ph.apply(lambda s: (s == "SECONDARY").mean())
    share_comb = ph.apply(lambda s: (s == "COMBINED").mean())
    ever_primary = ph.apply(lambda s: (s == "PRIMARY").any())
    ordinary = df.groupby("emis").type.agg(lambda s: s.str.contains("ORDINARY", na=False).mean() >= 0.5)

    phase = pd.Series("OUT", index=share_sec.index)
    phase[share_sec > 0.5] = "SECONDARY"
    phase[(share_comb > 0.5) & ~ever_primary] = "COMBINED"
    note("D9_combined_excluded_ever_primary", ((share_comb > 0.5) & ever_primary).sum())
    phase[~ordinary.reindex(phase.index, fill_value=False)] = "OUT"
    return phase


def main():
    raw = pd.read_csv(RAW_PANEL, low_memory=False)
    df = clean(raw)
    phase = school_population(df)
    df["phase"] = df.emis.map(phase).fillna("OUT")
    note("D9_schools_secondary", (phase == "SECONDARY").sum())
    note("D9_schools_combined", (phase == "COMBINED").sum())
    df = df[df.phase != "OUT"].copy()
    note("rows_out", len(df))
    note("schools_out", df.emis.nunique())

    cols = ["emis", "year", "province", "district", "district_key", "school", "status",
            "closing_flag", "sector", "phase", "phase_year", "quintile", "nofee",
            "urbanrural", "lat", "lon", "learners", "educators", "source_file"]
    df[cols].to_csv(CLEAN_PANEL, index=False, compression="gzip")
    with open(out("cleaning_log.json"), "w") as f:
        json.dump(log, f, indent=2)
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
