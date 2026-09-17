"""One variable at a time: how it is distributed, and how much it predicts.

Distribution works on any data. WoE and IV need a binary target, which depends
on the NSC matric results still being extracted, so those sections stay dormant
until a target column exists rather than inventing one.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.data import load_panel          # noqa: E402
from src.eda import woe as woe_lib              # noqa: E402
from src.features import clean                  # noqa: E402

st.set_page_config(page_title="Univariate", page_icon="📈", layout="wide")

TARGET_COLUMN = "is_high_risk"


@st.cache_data(show_spinner="Loading…")
def get_data():
    panel = load_panel()
    for column, cleaner in clean.CLEANERS.items():
        if column in panel.columns:
            panel[column] = panel[column].map(cleaner)
    panel["learners_n"] = panel["learners"].map(clean.count)
    panel["educators_n"] = panel["educators"].map(clean.count)
    panel["learner_educator_ratio"] = (panel["learners_n"] / panel["educators_n"]).round(1)
    return panel


data = get_data()
has_target = TARGET_COLUMN in data.columns

st.title("Univariate Analysis")
st.caption("Distribution, and predictive strength where a target exists")

CATEGORICAL = ["province", "phase", "quintile", "nofee", "urbanrural", "status", "sector"]
NUMERIC = ["learners_n", "educators_n", "learner_educator_ratio"]

variable = st.selectbox("Variable", CATEGORICAL + NUMERIC)
is_numeric = variable in NUMERIC

left, right = st.columns([2, 1])

with left:
    st.subheader("Distribution")
    if is_numeric:
        series = pd.to_numeric(data[variable], errors="coerce").dropna()
        upper = series.quantile(0.99)
        fig = px.histogram(series[series <= upper], nbins=60, height=420,
                           labels={"value": variable})
        fig.update_traces(marker_color="#2563eb")
        st.plotly_chart(fig, width='stretch')
        st.caption("Trimmed at the 99th percentile so a few extreme schools do not flatten the shape.")
    else:
        counts = data[variable].value_counts().reset_index()
        counts.columns = [variable, "rows"]
        fig = px.bar(counts, x=variable, y="rows", height=420)
        fig.update_traces(marker_color="#2563eb")
        st.plotly_chart(fig, width='stretch')

with right:
    st.subheader("Summary")
    if is_numeric:
        series = pd.to_numeric(data[variable], errors="coerce")
        st.dataframe(
            series.describe().round(2).rename("value").to_frame(),
            width='stretch',
        )
        st.metric("Missing", f"{int(series.isna().sum()):,}")
    else:
        counts = data[variable].value_counts()
        st.dataframe(counts.rename("rows").to_frame(), width='stretch')
        unknown = int((data[variable] == clean.UNKNOWN).sum())
        st.metric("UNKNOWN", f"{unknown:,}", f"{100 * unknown / len(data):.1f}% of rows")

st.divider()
st.subheader("Weight of Evidence and Information Value")

if not has_target:
    st.info(
        "**Waiting on the target variable.**\n\n"
        "WoE and IV both compare a variable against a binary outcome — here, "
        "whether a school is high-risk for losing learners. That outcome is "
        "built from NSC `Total Wrote` figures, which are still being extracted "
        "from the School Performance Report PDFs.\n\n"
        "Nothing is shown rather than something invented: a WoE table computed "
        "against a placeholder would look exactly as convincing as a real one."
    )

    with st.expander("What will appear here, and why it matters"):
        st.markdown(
            """
For each bin of the variable:

```
WoE = ln( share of low-risk schools / share of high-risk schools )
 IV = Σ ( share_low − share_high ) × WoE
```

**WoE** says which direction a bin pushes and how hard — quintile 1 will
push towards risk, quintile 5 away from it.

**IV** scores the whole variable in one number, so variables can be ranked
before any model is fitted. Conventional reading:

| IV | Meaning |
|---|---|
| < 0.02 | unpredictive |
| 0.02 – 0.1 | weak |
| 0.1 – 0.3 | medium |
| 0.3 – 0.5 | strong |
| > 0.5 | suspiciously strong — check for leakage |

That last band matters. An IV above 0.5 usually means the variable encodes
the answer rather than predicting it.

**The trap:** bins must be fitted on training data only. Fit them across
everything and every bin has seen the test set — AUC comes back inflated,
nothing errors, and the model disappoints on real data. `src/eda/woe.py`
separates `fit` from `transform` for exactly this reason.
            """
        )
else:
    table = woe_lib.woe_table(data[variable], data[TARGET_COLUMN])
    value = table["iv_contribution"].sum()

    a, b = st.columns(2)
    a.metric("Information Value", f"{value:.4f}")
    b.metric("Strength", woe_lib.iv_strength(value))

    fig = px.bar(table, x="bin", y="woe", height=380,
                 labels={"woe": "Weight of Evidence", "bin": variable})
    fig.update_traces(marker_color="#2563eb")
    st.plotly_chart(fig, width='stretch')
    st.dataframe(table.round(4), width='stretch', hide_index=True)
