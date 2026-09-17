"""Cached loaders and shared helpers for the app.

The app computes nothing of its own: every number is read from the pipeline's
outputs or re-scored with the saved scorecard (independent.src.scoring), so
the app and the report cannot disagree.
"""
import json

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from independent.src.paths import CLEAN_PANEL, MODEL_FRAME, RAW_PANEL, out
from independent.src.scoring import Scorecard
from independent.src.train import describe_bin

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
MUTED = "#b9b8b2"
INK_2 = "#52514e"

TIER_COLOR = {"PRIORITY": "#e34948", "WATCH": "#eda100", "": BLUE}
TIER_LABEL = {"PRIORITY": "Priority", "WATCH": "Watch", "": "Lower risk"}
PROVINCES = {"EC": "Eastern Cape", "FS": "Free State", "GP": "Gauteng", "KZN": "KwaZulu-Natal",
             "LP": "Limpopo", "MP": "Mpumalanga", "NC": "Northern Cape", "NW": "North West",
             "WC": "Western Cape"}
SHORT = {
    "log_learners": "School size",
    "vol": "Enrolment volatility",
    "quintile": "Poverty quintile",
    "chg1": "Last-year change",
    "peak_ratio": "Share of own peak",
    "province": "Province",
    "chg3": "Three-year trend",
    "edu_chg1": "Educator change",
    "district_schools": "FET schools in district",
    "district_chg1": "District trend",
}


@st.cache_resource
def scorecard():
    return Scorecard.load()


@st.cache_data
def model_json():
    with open(out("model.json")) as fh:
        return json.load(fh)


@st.cache_data
def read_json(name):
    with open(out(name)) as fh:
        return json.load(fh)


@st.cache_data
def read_csv(name):
    return pd.read_csv(out(name))


@st.cache_data(show_spinner="Loading the 2025 school list…")
def schools_2025():
    """One row per ranked school: ranking columns + raw features + location."""
    rank = pd.read_csv(out("ranking_2025.csv"))
    rank["tier"] = rank.tier.fillna("")
    for c in ("reason_1", "reason_2", "reason_3"):
        rank[c] = rank[c].fillna("")
    frame = pd.read_csv(MODEL_FRAME)
    frame = frame[frame.split == "score"].drop(
        columns=["school", "district", "learners", "province", "phase", "sector", "quintile"])
    geo = pd.read_csv(CLEAN_PANEL, usecols=["emis", "lat", "lon"]).drop_duplicates("emis")
    df = rank.merge(frame, on="emis", how="left").merge(geo, on="emis", how="left")
    df["quintile"] = rank.quintile
    df["province_name"] = df.province.map(PROVINCES)
    df["tier_label"] = df.tier.map(TIER_LABEL)
    df["label"] = (df["rank"].astype(str) + " · " + df.school.fillna("(unnamed)").str.title()
                   + " · " + df.district.fillna("").str.title())
    return df


@st.cache_data(show_spinner="Loading school histories…")
def panel():
    return pd.read_csv(CLEAN_PANEL, usecols=["emis", "year", "learners", "educators"])


@st.cache_data(show_spinner="Reading the raw national panel…")
def national_totals():
    raw = pd.read_csv(RAW_PANEL, usecols=["year", "learners"], low_memory=False)
    raw["learners"] = pd.to_numeric(raw.learners, errors="coerce")
    t = raw.groupby("year").learners.sum().div(1e6).reset_index(name="millions")
    t["status"] = np.where(t.year == 2017, "Dropped (corrupt)", "Kept")
    return t


def priority_cutoff():
    """Highest score that is still in the worst 10% of 2025."""
    return float(schools_2025().query("tier == 'PRIORITY'").score.max())


def tier_for(score, prob):
    if score <= priority_cutoff():
        return "PRIORITY"
    if prob >= scorecard().threshold:
        return "WATCH"
    return ""


def breakdown(row):
    """Per-feature points for one school, with the bin it fell in."""
    card = scorecard()
    frame = pd.DataFrame([row])
    pts = card.points(frame).iloc[0]
    best = card.best_points()
    rows = []
    for c in card.features:
        lab = card.bins[c].labels(frame[c]).iat[0]
        rows.append({
            "feature": c,
            "factor": SHORT[c],
            "value": describe_bin(c, lab),
            "points": float(pts[c]),
            "best": float(best[c]),
            "lost": float(best[c] - pts[c]),
        })
    return pd.DataFrame(rows).sort_values("lost", ascending=False)


def breakdown_chart(b):
    """Points lost against the best bin, per factor."""
    base = alt.Chart(b).encode(
        y=alt.Y("factor:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
        tooltip=[alt.Tooltip("factor:N", title="Factor"), alt.Tooltip("value:N", title="This school"),
                 alt.Tooltip("points:Q", title="Points", format=".1f"),
                 alt.Tooltip("best:Q", title="Best possible", format=".1f"),
                 alt.Tooltip("lost:Q", title="Points lost", format=".1f")],
    )
    bars = base.mark_bar(color=ORANGE, cornerRadiusEnd=4, height=16).encode(
        x=alt.X("lost:Q", title="Points lost against the best band",
                scale=alt.Scale(domainMax=max(float(b.lost.max()) * 1.6, 5))))
    text = base.mark_text(align="left", dx=4, color=INK_2, fontSize=11).encode(
        x="lost:Q", text=alt.Text("value:N"))
    return (bars + text).properties(height=34 * len(b))


def pct(v, digits=0):
    return "—" if pd.isna(v) else f"{v * 100:.{digits}f}%"


def fmt_int(v):
    return "—" if pd.isna(v) else f"{v:,.0f}"

