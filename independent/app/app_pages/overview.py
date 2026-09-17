import altair as alt
import pandas as pd
import streamlit as st

from independent.app.data import BLUE, MUTED, ORANGE, PROVINCES, model_json, read_json, schools_2025

m = model_json()["metrics"]
eda = read_json("eda_numbers.json")
log = read_json("cleaning_log.json")
df = schools_2025()

st.title("Which secondary schools are about to lose learners?")
st.markdown(
    "South Africa publishes how many learners leave school before matric, but not **which schools** "
    "they leave. This tool ranks every secondary and combined school on the risk that it loses "
    "learners faster than its province over the next two years, and says **why**."
)

with st.container(horizontal=True):
    st.metric("Schools scored for 2025", f"{len(df):,}", "secondary & combined, 100+ learners",
              delta_color="off", delta_arrow="off", border=True,
              help="Secondary and combined schools with at least 100 learners. Northern Cape has no 2025 masterlist.")
    st.metric("Priority schools", f"{(df.tier == 'PRIORITY').sum():,}", "worst 10% of scores",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Loss rate, highest-risk tenth", f"{eda['test_loss_rate_by_decile'][0]:.0%}",
              f"vs {eda['test_loss_rate_by_decile'][-1]:.1%} in the lowest-risk tenth",
              delta_color="off", delta_arrow="off", border=True,
              help="Measured on 2021–2023, years the model never saw.")
    st.metric("Test AUC", f"{m['scorecard_test']['auc']:.3f}",
              f"Gini {m['scorecard_test']['gini']:.2f} · tree benchmark {m['tree_test']['auc']:.3f}",
              delta_color="off", delta_arrow="off", border=True)

st.subheader("How it works")
a, b, c = st.columns(3)
with a.container(border=True, height="stretch"):
    st.markdown("**:material/database: 1 · Open data, cleaned**")
    st.markdown(
        f"{log['rows_in']:,} school-year rows from DBE masterlists, 2007–2025. "
        f"We found and fixed ten silent defects, including a corrupt 2017 snapshot, "
        f"{log['D4_latlon_swapped']:,} swapped coordinates and phase labels that change over time. "
        f"The result is **{log['rows_out']:,} rows covering {log['schools_out']:,} FET schools**."
    )
with b.container(border=True, height="stretch"):
    st.markdown("**:material/trending_down: 2 · A signal we can measure**")
    st.markdown(
        "The masterlist has no grade breakdown, so dropout can't be counted directly. We flag a "
        "school when its enrolment over two years falls **≥15 points more than its province's**. "
        f"That happens to {eda['loss_rate_overall']:.0%} of school-years, and the median flagged "
        f"school loses {eda['median_learners_lost_by_losers']:.0f} learners."
    )
with c.container(border=True, height="stretch"):
    st.markdown("**:material/scoreboard: 3 · A scorecard anyone can read**")
    st.markdown(
        "Ten factors, each split into bands worth a fixed number of points. **Lower score = higher "
        "risk.** Every school's list entry shows the three factors that cost it the most points, "
        "so an official can check them against the masterlist."
    )

left, right = st.columns([3, 2])
with left.container(border=True):
    st.markdown("**Priority schools by province, 2025**")
    counts = (df.assign(priority=df.tier == "PRIORITY")
              .groupby("province").agg(schools=("emis", "size"), priority=("priority", "sum"))
              .reset_index())
    counts["share"] = counts.priority / counts.schools
    counts["name"] = counts.province.map(PROVINCES)
    chart = alt.Chart(counts).mark_bar(cornerRadiusEnd=4, height=18).encode(
        y=alt.Y("name:N", sort="-x", title=None),
        x=alt.X("priority:Q", title="Priority schools",
                scale=alt.Scale(domainMax=float(counts.priority.max()) * 1.12)),
        color=alt.condition(alt.datum.priority > 150, alt.value(ORANGE), alt.value(BLUE)),
        tooltip=[alt.Tooltip("name:N", title="Province"), alt.Tooltip("priority:Q", title="Priority"),
                 alt.Tooltip("schools:Q", title="Schools scored"),
                 alt.Tooltip("share:Q", title="Share priority", format=".0%")],
    )
    labels = chart.mark_text(align="left", dx=4, color="#52514e").encode(text="priority:Q")
    st.altair_chart((chart + labels).properties(height=280))
    top3 = counts.nlargest(3, "priority")
    st.caption(f"{', '.join(top3.name)} hold {top3.priority.sum() / counts.priority.sum():.0%} of the "
               "priority list. Northern Cape is absent because its 2025 masterlist was not published.")

with right.container(border=True):
    st.markdown("**Does the ranking hold up on unseen years?**")
    dec = eda["test_loss_rate_by_decile"]
    d = pd.DataFrame({"decile": range(1, 11), "rate": dec})
    bars = alt.Chart(d).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("decile:O", title="Risk decile, 2021–2023 (1 = highest risk)", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("rate:Q", title="Share that lost learners", axis=alt.Axis(format="%")),
        color=alt.condition(alt.datum.decile == 1, alt.value(ORANGE), alt.value(BLUE)),
        tooltip=[alt.Tooltip("decile:O", title="Decile"), alt.Tooltip("rate:Q", title="Loss rate", format=".1%")],
    )
    avg = alt.Chart(pd.DataFrame({"y": [sum(dec) / 10]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((bars + avg).properties(height=280))
    st.caption("Schools the model ranks worst lose learners 8× as often as those it ranks best.")

st.subheader("Demo path")
with st.container(horizontal=True):
    st.page_link("app_pages/risk_list.py", label="1 · Filter the 2025 risk list", icon=":material/format_list_numbered:")
    st.page_link("app_pages/school.py", label="2 · Open one school and read its reasons", icon=":material/school:")
    st.page_link("app_pages/simulator.py", label="3 · Change a factor and watch the score move", icon=":material/tune:")
    st.page_link("app_pages/method.py", label="4 · Show why the numbers can be trusted", icon=":material/science:")
