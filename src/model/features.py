"""Building the predictors.

Raw columns describe a school at a moment. Risk is about direction and context,
so most of what the model uses is constructed here.

THE TIMING RULE, WHICH EVERYTHING ELSE FOLLOWS FROM

The outcome is observed in matric year Y. The enrolment it is measured against
is year Y-2, when that cohort was still in the school. So Y-2 is the moment a
prediction would actually be made, and every feature is computed as it stood
then, using that year and earlier only.

This is not caution for its own sake. A feature built from year Y would be
predicting the past from the future: the model would score beautifully in
testing and have nothing to say about a cohort still in school, which is the
only cohort anyone can still help.

Each feature is computed per school per year, from that year backwards. The
training table then joins matric year Y to features at year Y-2.
"""
import numpy as np
import pandas as pd

# Cape Town, Johannesburg, Durban, Gqeberha, Bloemfontein, Polokwane.
# Distance to the nearest of these stands in for isolation, measured rather
# than inferred from an urban/rural label that is missing on many records.
CITIES = [(-33.92, 18.42), (-26.20, 28.05), (-29.86, 31.02),
          (-33.96, 25.60), (-29.12, 26.21), (-23.90, 29.47)]

EARTH_RADIUS_KM = 6371


def _haversine(lat, lon, city_lat, city_lon):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat, lon, city_lat, city_lon])
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def distance_to_city(lat, lon):
    """Kilometres to the nearest major centre, or NaN where unusable."""
    lat = pd.to_numeric(lat, errors="coerce")
    lon = pd.to_numeric(lon, errors="coerce")
    # Latitude zero is the Atlantic Ocean, not a school.
    usable = lat.notna() & lon.notna() & (lat != 0) & (lon != 0)
    best = pd.Series(np.nan, index=lat.index, dtype=float)
    for city_lat, city_lon in CITIES:
        d = _haversine(lat.where(usable), lon.where(usable), city_lat, city_lon)
        best = np.fmin(best, d) if best.notna().any() else d
    return best


def build(panel):
    """Per school per year, using that year and earlier only.

    Requires emis, year, learners, educators, province, district, phase,
    quintile, nofee, urbanrural, lat, lon.
    """
    frame = panel.copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["learners"] = pd.to_numeric(frame["learners"], errors="coerce")
    frame["educators"] = pd.to_numeric(frame["educators"], errors="coerce")
    frame = frame.dropna(subset=["emis", "year", "learners"])
    frame = frame.sort_values(["emis", "year"]).reset_index(drop=True)

    by_school = frame.groupby("emis", sort=False)

    # --- enrolment direction -------------------------------------------------
    # shift() looks backwards only, so no future year can reach a feature.
    for span in (1, 3, 5):
        previous = by_school["learners"].shift(span)
        frame[f"enrolment_change_{span}y"] = (
            (frame["learners"] - previous) / previous.replace(0, np.nan))

    # Instability is a warning independent of direction: a school swinging by
    # hundreds of learners is not in control of its intake either way.
    frame["enrolment_volatility"] = (
        by_school["learners"]
        .transform(lambda s: s.shift(1).rolling(5, min_periods=3).std()
                   / s.shift(1).rolling(5, min_periods=3).mean()))

    # --- staffing ------------------------------------------------------------
    # A ratio rather than both counts: learners and educators correlate at
    # 0.89, so including both splits the coefficient unpredictably between them
    # and makes an individual score impossible to explain.
    frame["learner_educator_ratio"] = (
        frame["learners"] / frame["educators"].replace(0, np.nan))

    # --- context -------------------------------------------------------------
    # Absolute size means different things in a metro and a rural district, and
    # measured ratios turned out to be nearly flat across funding bands 1-4, so
    # relative position carries more signal than the raw value.
    district_median = frame.groupby(["district", "year"])["learners"].transform("median")
    frame["size_vs_district"] = frame["learners"] / district_median.replace(0, np.nan)

    province_ratio = (frame.groupby(["province", "year"])["learner_educator_ratio"]
                      .transform("median"))
    frame["ratio_vs_province"] = (
        frame["learner_educator_ratio"] / province_ratio.replace(0, np.nan))

    # --- structure -----------------------------------------------------------
    first_seen = by_school["year"].transform("min")
    frame["school_age"] = frame["year"] - first_seen

    # A merged or renumbered school loses learners for administrative reasons
    # and would otherwise read as severe attrition.
    if {"old_emis", "new_emis"}.issubset(frame.columns):
        old = frame["old_emis"].astype("string").str.strip()
        new = frame["new_emis"].astype("string").str.strip()
        frame["renumbered"] = ((old.notna() & (old != "") & (old != "0"))
                               & (new.notna() & (new != "") & (new != "0"))
                               & (old != new)).astype(int)
    else:
        frame["renumbered"] = 0

    frame["distance_to_city_km"] = distance_to_city(frame["lat"], frame["lon"])

    return frame


FEATURE_COLUMNS = [
    "enrolment_change_1y", "enrolment_change_3y", "enrolment_change_5y",
    "enrolment_volatility", "learner_educator_ratio", "size_vs_district",
    "ratio_vs_province", "school_age", "renumbered", "distance_to_city_km",
    "quintile", "nofee", "urbanrural", "province", "phase",
]


def training_table(panel, labels, lag=2):
    """Join outcomes at matric year Y to features as they stood at year Y-2.

    The lag is what keeps the table honest: it forces every predictor to
    predate the outcome it is paired with.
    """
    engineered = build(panel)

    available = [c for c in FEATURE_COLUMNS if c in engineered.columns]
    features = engineered[["emis", "year"] + available].copy()

    # Present the features under the matric year they will be judged against.
    features["year"] = features["year"] + lag

    outcomes = labels[["emis", "year", "is_high_risk", "survival_index",
                       "throughput", "wrote", "enrolment_before"]].copy()

    return outcomes.merge(features, on=["emis", "year"], how="inner")
