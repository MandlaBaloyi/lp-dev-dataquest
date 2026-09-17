"""Entry point for the EDA app.

Run from the repository root:

    streamlit run app/Home.py

This app holds no analysis logic. Every calculation it shows comes from src/,
so the pipeline and the app cannot disagree about what the data says. If a
number appears here, the same function produced it when the model was trained.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.data import load_panel          # noqa: E402
from src.common.paths import SCHOOL_PANEL       # noqa: E402

st.set_page_config(page_title="School Dropout EDA", page_icon="📊", layout="wide")


@st.cache_data(show_spinner="Loading the national school panel…")
def get_panel():
    return load_panel()


st.title("Early Warning System for School Dropout")
st.caption("South Africa · 2007–2025 · all nine provinces")

if not Path(SCHOOL_PANEL).exists():
    st.error(
        f"Panel not found at `{SCHOOL_PANEL}`.\n\n"
        "Build it first:\n\n"
        "```\npython -m src.fetch.emis_masterlists\npython -m src.build.school_panel\n```"
    )
    st.stop()

panel = get_panel()

st.subheader("What is in the raw data")

a, b, c, d = st.columns(4)
a.metric("School-year rows", f"{len(panel):,}")
b.metric("Distinct schools", f"{panel['emis'].nunique():,}")
c.metric("Years", f"{panel['year'].nunique()}")
d.metric("Provinces", f"{panel['province'].nunique()}")

st.markdown(
    """
This is the **raw** panel, exactly as the Department of Basic Education
publishes it, folded together from 234 provincial spreadsheets. It is not
clean. Roughly two thirds of these rows are primary schools, which cannot
have a matric cohort, and several columns carry the same fact under many
different spellings.

Working out what to keep, and recording why, is what this app is for.
"""
)

st.divider()
st.subheader("The work, in order")

st.markdown(
    """
| Page | What happens there |
|---|---|
| **1 · Data Quality** | What is missing, what is inconsistently spelled, what is impossible |
| **2 · Cleaning** | Decide the rules. Every choice shows what it costs in rows |
| **3 · Univariate** | One variable at a time: distribution, WoE, IV |
| **4 · Bivariate** | How variables move together, and against the target |
| **5 · Feature Engineering** | Binning, transformation, scorecard construction |
| **6 · Export** | Write the clean training table, with the decisions that made it |

Pages 3 and 5 need a target variable, which depends on the NSC matric results
still being extracted. They will show what they can until then.
"""
)

st.divider()
st.subheader("Where the data came from")

st.markdown(
    """
Every source is public and none required a login.

- **234 provincial masterlists** from the DBE EMIS Downloads page — one file
  per province per quarter, one row per school, carrying that year's learner
  and educator counts
- **13 NSC School Performance Reports**, 2012–2024 — each holds three years of
  matric results per school, and they chain without gaps

They join on the **EMIS number**, the national school identifier, after
normalising a leading zero that is inconsistent between sources.
"""
)

with st.expander("Four faults in the source data that raised no error"):
    st.markdown(
        """
Each of these was silent. Nothing crashed, the row counts looked reasonable,
and the data would simply have taught the model something untrue.

1. **2019 spells the key column `NatEMIS`**, every other year `NatEmis`.
   Matching exactly dropped the entire year while the panel still looked
   healthy at 450,000 rows.
2. **Province codes are unstable** — `KZ`/`KZN` and `GT`/`GP` — producing
   eleven provinces for a country with nine.
3. **Gauteng 2023 has its key column headed `"G"`**, truncated at source.
   Three thousand schools vanished. Recovered by inspecting the column's
   values rather than trusting its name.
4. **Phase is `Phase_PED` in newer files, `Phase_DoE` in older ones.** Phase is
   how a secondary school is identified, so losing it loses the population
   this project is about.
        """
    )

st.divider()
st.subheader("Sample of the raw data")
st.dataframe(panel.head(200), width='stretch', height=320)
