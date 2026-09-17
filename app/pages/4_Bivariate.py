"""How variables move together.

Two reasons this matters before modelling. Variables that correlate strongly
with each other carry the same information twice, which destabilises a linear
model's coefficients and makes them uninterpretable - fatal when the whole
point is explaining why a school scored as it did. And relationships that are
not straight lines have to be found by looking, because a correlation
coefficient reports a U-shape as no relationship at all.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.data import load_panel      # noqa: E402
from src.features import clean              # noqa: E402

st.set_page_config(page_title="Bivariate", page_icon="🔗", layout="wide")


@st.cache_data(show_spinner="Loading…")
def get_data():
    panel = load_panel()
    for column, cleaner in clean.CLEANERS.items():
        if column in panel.columns:
            panel[column] = panel[column].map(cleaner)
    panel["learners_n"] = panel["learners"].map(clean.count)
    panel["educators_n"] = panel["educators"].map(clean.count)
    panel["learner_educator_ratio"] = (panel["learners_n"] / panel["educators_n"]).round(1)
    panel["year_n"] = pd.to_numeric(panel["year"], errors="coerce")
    panel["quintile_n"] = pd.to_numeric(panel["quintile"], errors="coerce")
    return panel


data = get_data()

st.title("Bivariate Analysis")
st.caption("Correlation, group differences, and relationships over time")

tab_corr, tab_group, tab_trend, tab_scatter = st.tabs(
    ["Correlation", "By group", "Over time", "Scatter"]
)

NUMERIC = ["learners_n", "educators_n", "learner_educator_ratio", "quintile_n", "year_n"]

with tab_corr:
    st.subheader("Correlation between numeric variables")
    method = st.radio("Method", ["spearman", "pearson"], horizontal=True,
                      help="Spearman ranks rather than values, so it survives "
                           "the heavy skew in school sizes. Pearson assumes a "
                           "straight line.")

    corr = data[NUMERIC].astype(float).corr(method=method).round(3)
    fig = px.imshow(corr, text_auto=True, aspect="auto", height=480,
                    color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
    st.plotly_chart(fig, width='stretch')

    st.info(
        "Look for pairs above roughly |0.8|. Those carry the same information "
        "twice: a linear model splits its coefficient between them "
        "unpredictably, and the explanation of why a school scored high stops "
        "being trustworthy — which is the one thing this project cannot "
        "afford to lose."
    )

with tab_group:
    st.subheader("Does a numeric variable differ across a category?")
    c1, c2 = st.columns(2)
    numeric = c1.selectbox("Numeric variable", NUMERIC, index=2)
    category = c2.selectbox("Category", ["quintile", "urbanrural", "province",
                                         "phase", "nofee", "sector"])

    frame = data[[category, numeric]].copy()
    frame[numeric] = pd.to_numeric(frame[numeric], errors="coerce")
    frame = frame.dropna()
    upper = frame[numeric].quantile(0.99)
    frame = frame[frame[numeric] <= upper]

    fig = px.box(frame, x=category, y=numeric, height=460, points=False)
    fig.update_traces(marker_color="#2563eb")
    st.plotly_chart(fig, width='stretch')

    stats = (frame.groupby(category)[numeric]
             .agg(rows="count", median="median", mean="mean", std="std")
             .round(2).sort_values("median", ascending=False))
    st.dataframe(stats, width='stretch')
    st.caption(
        "A category whose groups separate clearly here is carrying signal. One "
        "whose boxes all overlap probably is not, whatever its IV later says."
    )

with tab_trend:
    st.subheader("How the system has changed, 2007–2025")
    c1, c2 = st.columns(2)
    measure = c1.selectbox("Measure", ["learners_n", "educators_n",
                                       "learner_educator_ratio"], key="trend")
    split = c2.selectbox("Split by", ["province", "quintile", "urbanrural", "none"])

    frame = data[["year_n", measure] + ([split] if split != "none" else [])].copy()
    frame[measure] = pd.to_numeric(frame[measure], errors="coerce")
    frame = frame.dropna(subset=["year_n", measure])

    group = ["year_n"] + ([split] if split != "none" else [])
    trend = frame.groupby(group)[measure].median().reset_index()

    fig = px.line(trend, x="year_n", y=measure,
                  color=split if split != "none" else None,
                  markers=True, height=460, labels={"year_n": "year"})
    st.plotly_chart(fig, width='stretch')
    st.caption(
        "Medians, not means — a handful of very large schools would otherwise "
        "drag the line and hide what the typical school is doing."
    )

with tab_scatter:
    st.subheader("Two variables directly")
    c1, c2, c3 = st.columns(3)
    x = c1.selectbox("X", NUMERIC, index=0)
    y = c2.selectbox("Y", NUMERIC, index=1)
    colour = c3.selectbox("Colour", ["quintile", "urbanrural", "province", "none"])

    sample = data.sample(min(6000, len(data)), random_state=0).copy()
    sample[x] = pd.to_numeric(sample[x], errors="coerce")
    sample[y] = pd.to_numeric(sample[y], errors="coerce")
    sample = sample.dropna(subset=[x, y])

    fig = px.scatter(sample, x=x, y=y,
                     color=colour if colour != "none" else None,
                     opacity=0.45, height=520)
    st.plotly_chart(fig, width='stretch')
    st.caption(
        f"A {len(sample):,}-row sample — plotting all {len(data):,} points would "
        "render as a solid block and hide the shape."
    )
