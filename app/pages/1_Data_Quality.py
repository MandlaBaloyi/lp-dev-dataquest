"""Data quality report.

Separates missing from dirty, because they fail differently. Missing is visible
and honest - a blank cell announces itself. Dirty is invisible: a column holding
both "3" and "Q3" looks complete in every summary and splits one category into
two the moment a model reads it.
"""
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.data import load_panel      # noqa: E402
from src.eda import quality                 # noqa: E402

st.set_page_config(page_title="Data Quality", page_icon="🔍", layout="wide")


@st.cache_data(show_spinner="Loading…")
def get_panel():
    return load_panel()


@st.cache_data
def get_completeness(_panel):
    return quality.completeness(_panel)


@st.cache_data
def get_dirty(_panel):
    return quality.dirty_categoricals(_panel)


@st.cache_data
def get_impossible(_panel):
    return quality.impossible_values(_panel)


@st.cache_data
def get_coverage(_panel):
    return quality.coverage_matrix(_panel)


panel = get_panel()

st.title("Data Quality")
st.caption(f"{len(panel):,} rows · {panel['emis'].nunique():,} schools · raw, uncleaned")

tab_missing, tab_dirty, tab_impossible, tab_coverage = st.tabs(
    ["Missing", "Dirty values", "Impossible values", "Coverage"]
)

with tab_missing:
    st.subheader("How much of each column is present")
    comp = get_completeness(panel)

    fig = px.bar(
        comp, x="filled_pct", y="column", orientation="h",
        labels={"filled_pct": "% of rows filled", "column": ""},
        range_x=[0, 100], height=520,
    )
    fig.update_traces(marker_color="#2563eb")
    st.plotly_chart(fig, width='stretch')

    st.dataframe(comp, width='stretch', hide_index=True)
    st.info(
        "A high fill rate is necessary but not sufficient. `quintile` is 97% "
        "filled and still unusable, because a filled cell may hold "
        "`TO BE UPDATED`. Completeness cannot see that — the next tab can."
    )

with tab_dirty:
    st.subheader("Columns carrying more values than the field can hold")
    dirty = get_dirty(panel)

    st.dataframe(
        dirty, width='stretch', hide_index=True,
        column_config={
            "distinct_raw": st.column_config.NumberColumn("distinct values found"),
            "expected": st.column_config.NumberColumn("values it should have"),
            "excess": st.column_config.NumberColumn("spellings to map"),
        },
    )
    st.warning(
        "`excess` is the number of extra spellings a model would read as "
        "separate categories. Every one of them splits signal that belongs "
        "together."
    )

    st.divider()
    st.subheader("Inspect a column")
    column = st.selectbox(
        "Column", list(quality.CATEGORICAL_EXPECTATIONS), index=0,
    )
    counts = quality.value_counts(panel, column)
    st.dataframe(counts, width='stretch', hide_index=True, height=420)
    st.caption(
        "`cleaned_to` shows where each raw spelling lands under the current "
        "rules in `src/features/clean.py`. The app does not define these rules; "
        "it reads the same ones the pipeline uses."
    )

with tab_impossible:
    st.subheader("Values that are well-formed but cannot be true")
    imp = get_impossible(panel)
    st.dataframe(imp, width='stretch', hide_index=True)
    st.error(
        "These pass every type check and every missing-value report. Latitude 0 "
        "is a valid number in a numeric column and a point in the Atlantic "
        "Ocean off west Africa. Any distance feature built on it is wrong, and "
        "any map drawn from it puts schools at sea."
    )

with tab_coverage:
    st.subheader("Rows by year and province")
    cov = get_coverage(panel)

    fig = px.imshow(
        cov, aspect="auto", color_continuous_scale="Blues",
        labels={"x": "province", "y": "year", "color": "schools"}, height=560,
    )
    st.plotly_chart(fig, width='stretch')

    st.dataframe(cov, width='stretch')
    st.info(
        "Gaps are visible here that a total would hide. Northern Cape has no "
        "2025 row: DBE published a Word template into that slot on their "
        "downloads page, not a spreadsheet. It is a source-side fault, and it "
        "matters only because a model would otherwise read it as a province "
        "that stopped existing."
    )
