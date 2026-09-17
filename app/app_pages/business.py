"""The operating model, with figures.

Estimates are marked as estimates. Every one is derived from published South
African salary and cloud pricing rather than invented, and the assumptions are
stated so a judge can disagree with them specifically rather than generally.
"""
import altair as alt
import pandas as pd
import streamlit as st

from app.data import BLUE, MUTED, ORANGE

SCHOOLS = 12_443
PRIORITY = 842

st.title("What it costs, and who pays")
st.markdown(
    "This is a tool for the people who allocate support, not a product sold to "
    "the schools that need it. That decides everything else about the model."
)

with st.container(horizontal=True):
    st.metric("Annual running cost", "R612,000", "estimated, year one",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Cost per school scored", "R49", f"across {SCHOOLS:,} schools",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Break-even", "4 provinces", "at R150,000 each",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Data acquisition cost", "R0", "every source is public",
              delta_color="off", delta_arrow="off", border=True)

st.divider()
st.subheader("What the problem costs")

st.markdown(
    "A business case needs both halves. The cost of the tool is easy to state and "
    "meaningless on its own — it only means something against the cost of not having it."
)

a, b, c = st.columns(3)
with a.container(border=True, height="stretch"):
    st.markdown(":material/groups: **212,893 learners**")
    st.caption(
        f"sit in the {PRIORITY:,} schools this register flags as priority for 2025. That is "
        "the population the list is pointing at.")
with b.container(border=True, height="stretch"):
    st.markdown(":material/trending_down: **90 learners**")
    st.caption(
        "is the median two-year enrolment drop at a flagged school that does go on to "
        "lose them — measured across 2,807 such cases in the test years, not assumed. "
        "Applied to the 28.5% of the priority tier that loses, that is roughly 21,600 "
        "learners.")
with c.container(border=True, height="stretch"):
    st.markdown(":material/school: **~R200,000 per learner**")
    st.caption(
        "is roughly what the state has already spent educating a learner by the time they "
        "reach Grade 10, at published per-learner spending of about R20,000 a year. An "
        "estimate, and a conservative one.")

st.error(
    """**The comparison that matters.** Running this costs **R612,000 a year**. The state
has already invested more than that in **three learners** who reach Grade 10. If the
register changes where support goes for even a handful of the 21,600 learners at risk in
the schools it flags, it has paid for itself many times over.

That is the argument — not that the tool is cheap, but that it is negligible against what
is already being spent on the learners it is trying to keep in school."""
)

st.divider()
st.subheader("What we spend")

costs = pd.DataFrame([
    ("Data analyst (full-time)", 420_000, "Maintains the pipeline, re-runs the audit each quarter, re-validates the model annually"),
    ("Engineering (part-time, 0.3)", 120_000, "Application, deployment, fixes when a source file changes shape"),
    ("Cloud hosting and storage", 24_000, "Small VM, object storage, backups. The datasets are under 100MB compressed"),
    ("Stakeholder engagement", 36_000, "Travel and workshops with provincial districts during onboarding"),
    ("Contingency", 12_000, "Tooling, domain, incidentals"),
], columns=["item", "rand", "why"])
costs.loc[len(costs)] = ("Total", costs.rand.sum(), "")

st.dataframe(
    costs, hide_index=True, use_container_width=True,
    column_config={
        "item": st.column_config.TextColumn("Cost", width="medium"),
        "rand": st.column_config.NumberColumn("Per year", format="R%d"),
        "why": st.column_config.TextColumn("What it buys", width="large"),
    })

st.caption(
    "Salary figures are mid-range South African market rates for 2026. Data "
    "acquisition is genuinely zero: all 234 spreadsheets and 13 reports are "
    "published openly and fetched by script."
)

st.divider()
st.subheader("Who pays, and why they would")

revenue = [
    (":material/account_balance:", "Provincial education departments",
     "R150,000 per province per year",
     "Nine possible customers. A province already employs planners who decide "
     "where support goes; this replaces guesswork in that decision, and costs "
     "less than one junior post."),
    (":material/volunteer_activism:", "NGOs running retention programmes",
     "R25,000 per organisation per year",
     "An organisation with funding for twelve schools currently chooses them by "
     "presence and reputation. This tells them which twelve, nationally."),
    (":material/savings:", "Grant funding, year one",
     "R500,000 – R750,000",
     "Education-focused funders already finance work on exactly this problem. "
     "Year one is grant-funded while the pilot proves itself, which removes the "
     "need to sell before there is evidence."),
]

for icon, name, price, text in revenue:
    with st.container(border=True):
        left, right = st.columns([3, 1])
        left.markdown(f":{icon.strip(':')}: **{name}**")
        left.caption(text)
        right.markdown(f"**{price}**")

st.divider()
st.subheader("Three years")

plan = pd.DataFrame([
    ("Year 1", "Grant-funded pilot, two provinces", 612_000, 600_000, -12_000),
    ("Year 2", "Four provinces paying, six NGOs", 680_000, 750_000, 70_000),
    ("Year 3", "All nine provinces, national rollout", 820_000, 1_500_000, 680_000),
], columns=["year", "stage", "cost", "income", "net"])

st.dataframe(
    plan, hide_index=True, use_container_width=True,
    column_config={
        "year": st.column_config.TextColumn("", width="small"),
        "stage": st.column_config.TextColumn("Stage", width="large"),
        "cost": st.column_config.NumberColumn("Cost", format="R%d"),
        "income": st.column_config.NumberColumn("Income", format="R%d"),
        "net": st.column_config.NumberColumn("Net", format="R%d"),
    })

chart_data = plan.melt(id_vars="year", value_vars=["cost", "income"],
                       var_name="kind", value_name="rand")
st.altair_chart(
    alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("year:N", title=None),
        y=alt.Y("rand:Q", title="Rand per year", axis=alt.Axis(format="~s")),
        color=alt.Color("kind:N", title=None,
                        scale=alt.Scale(domain=["cost", "income"],
                                        range=[MUTED, BLUE])),
        xOffset="kind:N",
        tooltip=["year", "kind", alt.Tooltip("rand:Q", format=",")]),
    use_container_width=True)

st.divider()
st.subheader("Why it survives after the hackathon")

a, b, c = st.columns(3)
with a.container(border=True, height="stretch"):
    st.markdown(":material/cloud_download: **The data costs nothing**")
    st.caption(
        "Every input is published openly and fetched by script. There is no "
        "licence to renew, no vendor to depend on, and no acquisition cost that "
        "grows with scale.")
with b.container(border=True, height="stretch"):
    st.markdown(":material/public: **It is already national**")
    st.caption(
        "All nine provinces are in the data from day one, because the source "
        "publishes all nine. Adding a province is a filter, not a project — so "
        "the tenth customer costs almost nothing to serve.")
with c.container(border=True, height="stretch"):
    st.markdown(":material/autorenew: **Refresh is a script, not a rebuild**")
    st.caption(
        "New masterlists are published quarterly. Re-running the pipeline is two "
        "commands, so staying current is an afternoon a quarter rather than a "
        "funded project.")

st.divider()
st.info(
    "**The honest framing.** At R49 per school per year, the question is not "
    "whether this is affordable — it is whether the ranking is good enough to "
    "act on. That is why the model's accuracy is reported plainly rather than "
    "flattered: the business case rests on it being trusted, and a number that "
    "does not survive scrutiny is worth less than no number at all."
)
