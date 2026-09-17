import altair as alt
import pandas as pd
import streamlit as st

from independent.app.data import (BLUE, MUTED, ORANGE, PROVINCES, TIER_LABEL, breakdown, breakdown_chart,
                                  fmt_int, panel, pct, schools_2025)

df = schools_2025()

# Arriving from the risk list pre-selects that school; otherwise start at rank 1.
labels = df.label.tolist()
current = st.session_state.emis
index = int(df.index[df.emis == current][0]) if current in set(df.emis) else 0
choice = st.selectbox("School", labels, index=index, key=f"sp_select_{current}",
                      help="Type to search by name, district or rank.")
row = df[df.label == choice].iloc[0]
st.session_state.emis = int(row.emis)

st.title(row.school.title())
with st.container(horizontal=True):
    tier_color = {"PRIORITY": "orange", "WATCH": "yellow", "": "blue"}[row.tier]
    st.badge(TIER_LABEL[row.tier], color=tier_color, icon=":material/flag:")
    st.badge(PROVINCES[row.province], color="gray")
    st.badge(str(row.district).title(), color="gray")
    st.badge(row.phase.title(), color="gray")
    st.badge(row.sector.title(), color="gray")
    st.badge("Quintile " + ("unknown" if pd.isna(row.quintile) else str(int(row.quintile))), color="gray")
    st.badge(f"EMIS {row.emis}", color="gray")

hist = panel()
hist = hist[hist.emis == row.emis].sort_values("year")

with st.container(horizontal=True):
    st.metric("National rank", f"{row['rank']:,} of {len(df):,}", border=True,
              help="1 = highest risk")
    st.metric("Score", f"{row.score:.0f}", f"priority cut-off {df[df.tier == 'PRIORITY'].score.max():.0f}",
              delta_color="off", delta_arrow="off", border=True, help="Lower = higher risk")
    st.metric("Chance of losing learners by 2027", pct(row.p_loss), f"national average {df.p_loss.mean():.0%}",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Learners, 2025", fmt_int(row.learners), border=True,
              chart_data=hist.learners.dropna().tolist()[-10:], chart_type="line")

b = breakdown(row)
left, right = st.columns([1, 1])
with left.container(border=True):
    st.markdown("**Why this score**")
    for i, r in enumerate(b.head(3).itertuples(), 1):
        if r.lost > 0.5:
            st.markdown(f"{i}. **{r.factor}**: {r.value}. Costs **{r.lost:.0f} points** against the best band.")
    st.altair_chart(breakdown_chart(b))
    st.caption("Each factor is worth between roughly 45 and 68 points. Bars show how far this school "
               "sits below the best band of each factor.")

with right.container(border=True):
    st.markdown("**Enrolment history**")
    h = hist.melt(id_vars="year", value_vars=["learners"], var_name="series", value_name="count").dropna()
    line = alt.Chart(h).mark_line(color=BLUE, strokeWidth=2, point=alt.OverlayMarkDef(size=40, color=BLUE)).encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("count:Q", title="Learners", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("count:Q", title="Learners", format=",.0f")],
    )
    now = alt.Chart(h[h.year == 2025]).mark_point(size=140, color=ORANGE, filled=True).encode(x="year:O", y="count:Q")
    st.altair_chart((line + now).properties(height=260))
    st.caption("2017 is missing on purpose: that year's national snapshot is corrupt and was dropped.")

    st.markdown("**Educators**")
    e = hist.dropna(subset=["educators"])
    if e.empty:
        st.caption("No educator counts published.")
    else:
        bars = alt.Chart(e).mark_bar(color=MUTED, cornerRadiusEnd=3).encode(
            x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("educators:Q", title="Educators"),
            tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("educators:Q", title="Educators")],
        )
        st.altair_chart(bars.properties(height=150))

with st.container(border=True):
    st.markdown("**Highest-risk schools in the same district**")
    near = df[(df.district == row.district) & (df.emis != row.emis)].nsmallest(8, "score")
    if near.empty:
        st.caption("No other ranked schools in this district.")
    else:
        st.dataframe(near[["rank", "school", "learners", "score", "tier_label", "reason_1"]], hide_index=True,
                     column_config={"rank": "Rank", "school": "School", "learners": st.column_config.NumberColumn("Learners", format="%d"),
                                    "score": "Score", "tier_label": "Tier", "reason_1": "Top reason"})

st.page_link("app_pages/simulator.py", label="What would change this school's score? Open the simulator",
             icon=":material/tune:")
