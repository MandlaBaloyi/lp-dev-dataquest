import altair as alt
import pandas as pd
import streamlit as st

from independent.app.data import BLUE, MUTED, ORANGE, PROVINCES, model_json, read_json, schools_2025

model = model_json()
m = model["metrics"]
audit = read_json("data_audit_summary.json")
eda = read_json("eda_numbers.json")
log = read_json("cleaning_log.json")
df = schools_2025()

st.title("Which secondary schools are about to lose learners?")
st.markdown(
    "More than 40% of South African learners who start Grade 1 never finish matric. That figure is "
    "published every year. What does not exist, anywhere, is the same figure **school by school** — "
    "so support goes where there is information, and at school level that information has never "
    "been assembled."
)
st.markdown(
    "This tool assembles it. It audits every school record the country publishes, repairs what it "
    "finds, then ranks every secondary and combined school on the risk of losing learners faster "
    "than its province over the next two years — and says **why** for each one."
)

st.divider()
st.subheader("The question behind the question")
st.markdown(
    "*How do we save those learners?* cannot be answered until four smaller ones are. "
    "**None of them currently has an answer anywhere in the public record.** We can now answer three."
)

questions = pd.DataFrame([
    ("Which provinces are losing the most?",
     f"All {df.province.nunique()}, ranked by measured risk rather than estimate", "Answered"),
    ("Which districts inside those provinces?",
     f"All {df.district.nunique()}, ranked within their province", "Answered"),
    ("Which schools inside those districts?",
     f"All {len(df):,} secondary schools, scored and ranked individually", "Answered"),
    ("Which grades inside those schools?",
     "Needs per-grade enrolment, held under separate permission", "Not yet"),
], columns=["Question", "What the register delivers", "Status"])

st.dataframe(
    questions, hide_index=True, width="stretch",
    column_config={
        "Question": st.column_config.TextColumn(width="medium"),
        "What the register delivers": st.column_config.TextColumn(width="large"),
        "Status": st.column_config.TextColumn(width="small"),
    })

st.caption(
    "On the fourth we are deliberate. We can say a school is losing its Grade 8–12 pipeline. "
    "We cannot yet say whether the loss concentrates in Grade 10 or Grade 11 — that needs a "
    "dataset held under separate permission. It is a form, not a rebuild: the same pipeline "
    "answers the fourth question the moment it arrives."
)
st.divider()

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
a, b, c, d = st.columns(4)
with a.container(border=True, height="stretch"):
    st.markdown("**:material/rule: 1 · Audit the data first**")
    st.markdown(
        f"Seven automated detectors over {audit['records_scanned']:,} published school records. "
        f"They return **{audit['total_findings']} discrepancies, {audit['high']} severe** — a year "
        "that loses 1.4 million learners and gets them back, a province published under two codes, "
        "schools placed in the Atlantic Ocean. None of them raises an error."
    )
with b.container(border=True, height="stretch"):
    st.markdown("**:material/trending_down: 2 · A signal we can measure**")
    st.markdown(
        "The masterlist has no grade breakdown, so dropout can't be counted directly. We flag a "
        "school when its enrolment over two years falls **≥15 points more than its province's**. "
        f"That happens to {eda['loss_rate_overall']:.0%} of school-years, and the median flagged "
        f"school loses {eda['median_learners_lost_by_losers']:.0f} learners. Measured against the "
        "province, so a provincial policy shift is not read as thousands of failing schools."
    )
MATRIC_PREFIXES = ("throughput", "wrote_", "pass_rate", "progressed_", "matric_")
matric_kept = [f for f in model["features_in_model"] if f.startswith(MATRIC_PREFIXES)]

with c.container(border=True, height="stretch"):
    st.markdown("**:material/school: 3 · Add the matric evidence**")
    st.markdown(
        f"{audit['matric_records']:,} matric records extracted from 13 exam report PDFs, no two of "
        "which share a column layout. They carry what a headcount cannot: how many learners "
        f"actually reached the end of school. **{len(matric_kept)} of those variables earned a "
        "place in the final model**, and the strongest single factor in it is one of them."
    )

with d.container(border=True, height="stretch"):
    st.markdown("**:material/scoreboard: 4 · A scorecard anyone can read**")
    st.markdown(
        f"{len(model['features_in_model'])} factors, each split into bands worth a fixed number of "
        "points. **Lower score = higher risk.** Every school shows the three factors that cost it "
        "the most, so an official can check them against the source."
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
    st.caption("Schools the model ranks worst lose learners 12× as often as those it ranks best — 28.5% against 2.4%, on years it never saw.")

st.subheader("Where to go next")
with st.container(horizontal=True):
    st.page_link("app_pages/data_audit.py", label="1 · What is wrong with the data",
                 icon=":material/rule:")
    st.page_link("app_pages/final_model.py", label="2 · The model, and every number it is judged on",
                 icon=":material/analytics:")
    st.page_link("app_pages/risk_list.py", label="3 · The 2025 register",
                 icon=":material/format_list_numbered:")
    st.page_link("app_pages/school.py", label="4 · One school and its reasons",
                 icon=":material/school:")
