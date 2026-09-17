import altair as alt
import pandas as pd
import streamlit as st

from app.data import BLUE, MUTED, ORANGE, PROVINCES, model_json, read_json, schools_2025

model = model_json()
m = model["metrics"]
audit = read_json("data_audit_summary.json")
eda = read_json("eda_numbers.json")
log = read_json("cleaning_log.json")
df = schools_2025()

st.title("The Missing List")
st.caption("A school-level dropout risk register for South Africa")

st.markdown(
    "**More than 40% of South African learners who start Grade 1 never finish matric.** "
    "Put plainly: 40 of every 100 children who walk into a Grade 1 classroom will not walk "
    "out of a Grade 12 one. That figure is published, widely quoted, and not in dispute."
)
st.markdown("### So the obvious question is: how do we save those learners?")

st.markdown(
    "That is the real problem — and it is not that the number is unknown. It is well known. "
    "It is that **it cannot be pointed at anything.** Nobody can deploy a teacher to a "
    "percentage. An organisation with one retention programme and funding for twelve schools "
    "cannot use a national average to choose the twelve. Learners are counted after they are "
    "gone, in aggregate, once a year."
)
st.markdown(
    "*Every year that list does not exist, help goes somewhere — just not necessarily where "
    "the loss is worst.*"
)

st.divider()
st.subheader("Four questions stand in the way")
st.markdown(
    "Before *how do we save them* can be answered, four smaller questions have to be. "
    "**None of them currently has an answer anywhere in the public record.** "
    "This register answers three."
)

questions = pd.DataFrame([
    ("Which provinces are losing the most?",
     f"{df.province.nunique()} of 9, ranked by measured risk rather than estimate", "Answered"),
    ("Which districts inside those provinces?",
     f"{df.district.nunique()}, ranked within their province", "Answered"),
    ("Which schools inside those districts?",
     f"{len(df):,} secondary and combined schools, scored and ranked individually", "Answered"),
    ("Which grades inside those schools?",
     "Needs per-grade enrolment, held under separate permission", "Not yet"),
], columns=["Question", "What the 2025 register delivers", "Status"])

st.dataframe(
    questions, hide_index=True, width="stretch",
    column_config={
        "Question": st.column_config.TextColumn(width="medium"),
        "What the register delivers": st.column_config.TextColumn(width="large"),
        "Status": st.column_config.TextColumn(width="small"),
    })

st.caption(
    f"**Why 8 provinces and not 9.** Northern Cape published a Word template into the slot "
    f"where its 2025 masterlist belonged, so the province has no 2025 data to score — a fault "
    f"the audit found rather than one we introduced. The model covers all nine; the register "
    f"covers the eight that published. Schools below 100 learners are also excluded, because "
    f"one learner leaving moves their rate by several points."
)
st.caption(
    "On the fourth question we are deliberate. We can say a school is losing its Grade 8–12 "
    "pipeline. We cannot yet say whether the loss concentrates in Grade 10 or Grade 11 — that "
    "needs a dataset held under separate permission. It is a form, not a rebuild: the same "
    "pipeline answers the fourth question the moment it arrives."
)

st.divider()
st.subheader("We build the missing list")
st.markdown(
    "Using 19 years of open government data covering every school in all nine provinces, we "
    "score each secondary school on its risk of losing learners before matric, rank them worst "
    "first, and attach the reasons."
)

a, b = st.columns(2)
with a.container(border=True, height="stretch"):
    st.markdown(":material/person_search: **What a user does with it**")
    st.markdown(
        "A planner opens the register, filters to their province, and sees the schools to act "
        "on first — each with a score, a national rank, and its three driving factors. "
        "**That is a morning's decision instead of a year's guesswork.**"
    )
with b.container(border=True, height="stretch"):
    st.markdown(":material/visibility: **Why it can be trusted**")
    st.markdown(
        "The model is a scorecard, not a black box. Every score decomposes into visible, "
        "auditable weights, so whoever must justify the spend can **explain the decision line "
        "by line** — to a treasury, a community, or a school that disagrees with it."
    )

st.markdown(
    "A ranking alone says where to go but not what to bring. Each score breaks into the factors "
    "that produced it — funding tier, staffing levels, enrolment trend, matric throughput — "
    "because a school flagged for a funding reason needs different help from one flagged for a "
    "staffing reason."
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
