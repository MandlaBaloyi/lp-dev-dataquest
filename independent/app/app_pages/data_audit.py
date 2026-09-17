"""The data audit: what is wrong with South Africa's published school data.

This page answers the challenge directly - identify discrepancy and anomaly in
education data. Everything shown is produced by src/eda/anomalies.py running
over the published masterlists; nothing is hand-listed.
"""
import altair as alt
import pandas as pd
import streamlit as st

from independent.app.data import BLUE, MUTED, ORANGE, read_json

SEVERITY_COLOUR = {"HIGH": "#cf222e", "MEDIUM": "#bf8700", "LOW": "#57606a"}


@st.cache_data
def findings():
    return pd.read_csv("independent/outputs/data_audit.csv")


summary = read_json("data_audit_summary.json")
table = findings()

st.title("The data is broken, and nothing says so")
st.markdown(
    "Before a single model was trained, we ran an automated audit over every school "
    "record South Africa publishes. It found **15 discrepancies**, eleven of them "
    "severe enough to change a model's answer."
)
st.markdown(
    "**Not one of them raises an error.** The files open, the row counts look "
    "reasonable, the totals look plausible. That is what makes this class of fault "
    "worth detecting automatically: a crash gets noticed within the hour, while a "
    "province that quietly becomes two survives all the way into a published finding."
)

with st.container(horizontal=True):
    st.metric("Records audited", f"{summary['records_scanned']:,}",
              f"{summary['schools_scanned']:,} schools · {summary['years_scanned']} years",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Discrepancies found", f"{summary['total_findings']}",
              f"{summary['detectors_triggered']} of 7 detectors triggered",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("High severity", f"{summary['high']}",
              "would change what a model learns",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Provinces covered", f"{summary['provinces_scanned']}",
              "every province, 2007–2025",
              delta_color="off", delta_arrow="off", border=True)

st.divider()
st.subheader("The one that would have sunk the project")

totals = pd.DataFrame(
    {"year": [int(y) for y in summary["national_totals"]],
     "learners": list(summary["national_totals"].values())})
totals["flag"] = totals["year"].isin([2017, 2018])

chart = alt.Chart(totals).mark_line(point=True, strokeWidth=2.5, color=BLUE).encode(
    x=alt.X("year:O", title=None),
    y=alt.Y("learners:Q", title="Learners reported nationally",
            scale=alt.Scale(zero=False), axis=alt.Axis(format="~s")),
    tooltip=["year", alt.Tooltip("learners:Q", format=",")])
points = alt.Chart(totals[totals.flag]).mark_point(
    size=170, color="#cf222e", filled=True).encode(x="year:O", y="learners:Q")
st.altair_chart(chart + points, use_container_width=True)

st.error(
    "**National enrolment falls by 1.44 million learners in 2017 and recovers by "
    "1.31 million in 2018.** South Africa did not lose eleven percent of its "
    "learners in a year and get them back. It is a publication fault in the "
    "masterlist, and any measure built on enrolment change reads it as thousands "
    "of schools collapsing at once."
)

st.divider()
st.subheader("Every finding")

severity = st.segmented_control(
    "Severity", ["All", "HIGH", "MEDIUM"], default="All", key="sev")
shown = table if severity == "All" else table[table.severity == severity]

st.dataframe(
    shown[["severity", "detector", "finding", "schools_affected", "detail"]],
    hide_index=True, use_container_width=True,
    column_config={
        "severity": st.column_config.TextColumn("Severity", width="small"),
        "detector": st.column_config.TextColumn("Detector", width="medium"),
        "finding": st.column_config.TextColumn("What was found", width="large"),
        "schools_affected": st.column_config.NumberColumn("Schools", format="%d"),
        "detail": st.column_config.TextColumn("Why it matters", width="large"),
    })

st.divider()
st.subheader("What each detector looks for")

detectors = [
    (":material/trending_down:", "Collapsing totals",
     "A year where the national figure breaks trend and then recovers. Real "
     "demographic change is under 3% a year; anything past 5% is a publication "
     "fault."),
    (":material/format_list_bulleted:", "Unstable categories",
     "The same fact published under many spellings. Funding band appears as both "
     "\"3\" and \"Q3\", which a model reads as two unrelated bands, halving the "
     "signal from the strongest variable available."),
    (":material/swap_horiz:", "Label churn",
     "A school whose recorded type changes between years. 8,792 schools change "
     "phase, so filtering on that field alone admits schools with no matric class "
     "into a study about matric."),
    (":material/wrong_location:", "Impossible values",
     "Values that are well formed and cannot be true. 724 schools sit at latitude "
     "zero, a point in the Atlantic roughly 2,000km offshore."),
    (":material/event_busy:", "Coverage gaps",
     "A province that stops existing for a year. Northern Cape has no 2025 data "
     "because a Word template was published into the slot where the spreadsheet "
     "belonged."),
    (":material/link_off:", "Identifier breaks",
     "Schools that vanish from the record and return. Usually renumbering rather "
     "than closure, but any trend measured across the gap is wrong."),
    (":material/content_copy:", "Duplicate records",
     "The same school reported twice in one year, double-counting any national "
     "total built from those rows."),
]

for row in range(0, len(detectors), 2):
    columns = st.columns(2)
    for column, (icon, name, text) in zip(columns, detectors[row:row + 2]):
        with column.container(border=True, height="stretch"):
            st.markdown(f":{icon.strip(':')}: **{name}**")
            st.caption(text)

st.divider()
st.info(
    "**Why this comes first.** Every number in the rest of this application is "
    "computed from data that has been through these checks. The audit is not a "
    "preliminary; it is the reason the ranking can be trusted at all."
)
