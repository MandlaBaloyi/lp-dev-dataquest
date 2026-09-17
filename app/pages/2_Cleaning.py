"""Where the cleaning decisions get made and recorded.

Each control below is a judgement call. None has an objectively correct answer;
each one changes the population the model is trained on. Every choice shows its
cost in rows immediately, and is written to config/cleaning_decisions.json,
which the pipeline reads. The app does not clean anything itself - it decides,
and the pipeline obeys.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.data import load_panel          # noqa: E402
from src.features import clean, decisions       # noqa: E402

st.set_page_config(page_title="Cleaning", page_icon="🧹", layout="wide")


@st.cache_data(show_spinner="Loading…")
def get_panel():
    return load_panel()


@st.cache_data(show_spinner="Applying rules…")
def apply_rules(_panel):
    """Run the same normalisation the pipeline runs."""
    out = _panel.copy()
    for column, cleaner in clean.CLEANERS.items():
        if column in out.columns:
            out[column] = out[column].map(cleaner)
    out["learners_n"] = out["learners"].map(clean.count)
    out["educators_n"] = out["educators"].map(clean.count)
    return out


panel = get_panel()
cleaned = apply_rules(panel)
current = decisions.load()

st.title("Cleaning Decisions")
st.caption("Each choice changes what the model learns from. Each one is recorded.")

st.subheader("What normalisation alone achieves")
rows = []
for column in clean.CLEANERS:
    if column in panel.columns:
        rows.append({
            "column": column,
            "before": int(panel[column].astype("string").nunique()),
            "after": int(cleaned[column].nunique()),
        })
summary = pd.DataFrame(rows)
summary["collapsed"] = summary["before"] - summary["after"]
st.dataframe(summary, width='stretch', hide_index=True)
st.caption(
    "These are not judgement calls — `Q3` and `3` are the same funding tier. "
    "The rules live in `src/features/clean.py` and apply automatically."
)

st.divider()
st.header("The judgement calls")
st.markdown(
    "Below are choices where a reasonable person could go either way. "
    "**You will be asked to defend these**, so the reasoning matters more "
    "than the answer."
)

chosen = {}

with st.form("decisions"):
    left, right = st.columns(2)

    with left:
        st.markdown("**Which schools count**")

        phases = sorted(p for p in cleaned["phase"].unique() if p != clean.UNKNOWN)
        chosen["include_phases"] = st.multiselect(
            "School phases to include", phases,
            default=[p for p in current["include_phases"] if p in phases],
            help=decisions.EXPLANATIONS["include_phases"],
        )
        chosen["include_special_needs"] = st.checkbox(
            "Include special-needs schools and schools of skills",
            value=current["include_special_needs"],
            help=decisions.EXPLANATIONS["include_special_needs"],
        )
        chosen["drop_closing_schools"] = st.checkbox(
            "Drop schools marked as closing",
            value=current["drop_closing_schools"],
            help=decisions.EXPLANATIONS["drop_closing_schools"],
        )
        chosen["min_learners"] = st.number_input(
            "Minimum learners for a school to be usable",
            min_value=0, max_value=500, value=int(current["min_learners"]), step=5,
            help=decisions.EXPLANATIONS["min_learners"],
        )

    with right:
        st.markdown("**How to treat missing and edge values**")

        chosen["drop_unknown_quintile"] = st.checkbox(
            "Drop rows with no usable quintile",
            value=current["drop_unknown_quintile"],
            help=decisions.EXPLANATIONS["drop_unknown_quintile"],
        )
        chosen["require_educator_count"] = st.checkbox(
            "Require an educator count",
            value=current["require_educator_count"],
            help=decisions.EXPLANATIONS["require_educator_count"],
        )
        chosen["deep_rural_separate"] = st.checkbox(
            "Keep DEEP RURAL separate from RURAL",
            value=current["deep_rural_separate"],
            help=decisions.EXPLANATIONS["deep_rural_separate"],
        )

    submitted = st.form_submit_button("Save these decisions", type="primary")

if submitted:
    decisions.save(chosen)
    st.success(f"Saved to `{decisions.CONFIG}` — the pipeline will use these.")
    st.rerun()

st.divider()
st.header("What these decisions cost")

keep = cleaned.copy()
steps = [("Raw panel, every school type", len(keep))]

phase_filter = list(current["include_phases"])
if current["include_special_needs"]:
    phase_filter += ["SPECIAL", "SKILLS"]
keep = keep[keep["phase"].isin(phase_filter)]
steps.append((f"Phase in {', '.join(phase_filter)}", len(keep)))

if current["drop_closing_schools"]:
    keep = keep[keep["status"] == "OPEN"]
    steps.append(("Open schools only", len(keep)))

if current["min_learners"] > 0:
    keep = keep[keep["learners_n"].fillna(0) >= current["min_learners"]]
    steps.append((f"At least {current['min_learners']} learners", len(keep)))

if current["drop_unknown_quintile"]:
    keep = keep[keep["quintile"] != clean.UNKNOWN]
    steps.append(("Usable quintile", len(keep)))

if current["require_educator_count"]:
    keep = keep[keep["educators_n"].notna()]
    steps.append(("Educator count present", len(keep)))

waterfall = pd.DataFrame(steps, columns=["step", "rows_remaining"])
waterfall["rows_lost"] = waterfall["rows_remaining"].shift(1) - waterfall["rows_remaining"]
waterfall["% of raw"] = (100 * waterfall["rows_remaining"] / len(cleaned)).round(1)

st.dataframe(
    waterfall.fillna({"rows_lost": 0}), width='stretch', hide_index=True,
    column_config={"rows_lost": st.column_config.NumberColumn("rows lost", format="%d")},
)

a, b, c = st.columns(3)
a.metric("Rows kept", f"{len(keep):,}", f"-{len(cleaned) - len(keep):,}")
b.metric("Schools kept", f"{keep['emis'].nunique():,}")
c.metric("Share of raw data", f"{100 * len(keep) / len(cleaned):.1f}%")

departures = decisions.changed_from_default()
if departures:
    st.subheader("Decisions differing from the defaults")
    st.json(departures)
    st.caption("This is the audit trail. Be ready to explain each one.")
else:
    st.caption("All decisions are currently at their defaults.")
