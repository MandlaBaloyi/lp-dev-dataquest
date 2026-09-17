import numpy as np
import pandas as pd
import streamlit as st

from independent.app.data import (PROVINCES, SHORT, TIER_LABEL, breakdown, breakdown_chart, schools_2025,
                                  scorecard, tier_for)
from independent.src.train import describe_bin

df = schools_2025()
card = scorecard()

st.title("Score simulator")
st.caption("Start from a real school, change any factor, and watch the score respond. The scorecard is "
           "additive, so every change can be traced to one factor's points.")

labels = df.label.tolist()
current = st.session_state.emis
index = int(df.index[df.emis == current][0]) if current in set(df.emis) else 0
choice = st.selectbox("Start from", labels, index=index, key=f"sim_select_{current}")
base = df[df.label == choice].iloc[0]
st.session_state.emis = int(base.emis)
k = f"sim_{base.emis}"  # widget keys per school, so switching school resets the inputs


def val(col, default, lo=-np.inf, hi=np.inf):
    """The school's own value as a widget default, kept inside the widget's range."""
    v = base[col]
    return float(np.clip(default if pd.isna(v) else float(v), lo, hi))


inputs, result = st.columns([2, 3])
with inputs.container(border=True):
    st.markdown("**Factors**")
    learners = st.number_input("Learners", 100, 4000, int(val("learners", 400, 100, 4000)), step=25, key=f"{k}_l")
    st.markdown("Enrolment movement")
    chg1 = st.slider("Change over the last year", -40, 40, int(round(val("chg1", 0, -0.4, 0.4) * 100)),
                     format="%d%%", key=f"{k}_c1")
    chg3 = st.slider("Average yearly change over three years", -30, 30, int(round(val("chg3", 0, -0.3, 0.3) * 100)),
                     format="%d%%", key=f"{k}_c3")
    peak = st.slider("Enrolment as a share of the school's own peak", 20, 100,
                     int(round(val("peak_ratio", 1, 0.2, 1) * 100)), format="%d%%", key=f"{k}_pk")
    short_history = st.toggle("Fewer than four years of history", value=bool(pd.isna(base.vol)), key=f"{k}_nh")
    vol = st.slider("Enrolment volatility (sd of yearly log change)", 0.0, 0.5, round(val("vol", 0.09, 0, 0.5), 2),
                    step=0.01, disabled=short_history, key=f"{k}_v",
                    help="0.05 is a steady school; 0.2+ means enrolment swings by around a fifth a year.")
    st.markdown("School and area")
    q_opts = [1, 2, 3, 4, 5, "Unknown"]
    q = st.segmented_control("Poverty quintile", q_opts,
                             default="Unknown" if pd.isna(base.quintile) else int(base.quintile),
                             format_func=lambda o: o if o == "Unknown" else f"Q{o}", required=True, key=f"{k}_q")
    edu = st.slider("Educator change over the last year", -50, 50, int(round(val("edu_chg1", 0, -0.5, 0.5) * 100)),
                    format="%d%%", key=f"{k}_e")
    prov = st.selectbox("Province", list(PROVINCES), index=list(PROVINCES).index(base.province),
                        format_func=PROVINCES.get, key=f"{k}_p")
    dschools = st.number_input("FET schools in the district", 1, 300, int(val("district_schools", 100, 1, 300)),
                               key=f"{k}_ds")
    dchg = st.slider("District's typical yearly change", -10.0, 10.0, round(val("district_chg1", 0, -0.1, 0.1) * 200) / 2,
                     step=0.5, format="%.1f%%", key=f"{k}_dc")

scenario = base.copy()
scenario["log_learners"] = np.log1p(learners)
scenario["chg1"] = chg1 / 100
scenario["chg3"] = chg3 / 100
scenario["peak_ratio"] = peak / 100
scenario["vol"] = np.nan if short_history else vol
scenario["quintile"] = np.nan if q == "Unknown" else float(q)
scenario["edu_chg1"] = edu / 100
scenario["province"] = prov
scenario["district_schools"] = dschools
scenario["district_chg1"] = dchg / 100

frame = pd.DataFrame([base, scenario])
scores = card.score(frame)
probs = card.probability(frame)
s0, s1 = float(scores.iloc[0]), float(scores.iloc[1])
p0, p1 = float(probs.iloc[0]), float(probs.iloc[1])
t1 = tier_for(s1, p1)
# Published scores are whole numbers; rank against the other schools the same way.
others = df.score[df.emis != base.emis]
new_rank = int((others < round(s1)).sum()) + 1

with result:
    with st.container(horizontal=True):
        st.metric("Score", f"{s1:.0f}", f"{s1 - s0:+.0f} vs actual", border=True,
                  help="Higher = safer")
        st.metric("Chance of losing learners", f"{p1:.0%}", f"{(p1 - p0) * 100:+.1f} pts",
                  delta_color="inverse", border=True)
        st.metric("Tier", TIER_LABEL[t1], f"was {TIER_LABEL[base.tier]}", delta_color="off",
                  delta_arrow="off", border=True)
        st.metric("Would rank", f"{new_rank:,}", f"was {int(base['rank']):,}", delta_color="off",
                  delta_arrow="off", border=True)

    with st.container(border=True):
        st.markdown("**Points by factor**")
        b0 = breakdown(base).set_index("feature")
        b1 = breakdown(scenario).set_index("feature")
        comp = pd.DataFrame({
            "Factor": [SHORT[c] for c in card.features],
            "Actual band": [b0.loc[c, "value"] for c in card.features],
            "Actual pts": [b0.loc[c, "points"] for c in card.features],
            "Scenario band": [b1.loc[c, "value"] for c in card.features],
            "Scenario pts": [b1.loc[c, "points"] for c in card.features],
        })
        comp["Change"] = comp["Scenario pts"] - comp["Actual pts"]
        st.dataframe(comp, hide_index=True, column_config={
            "Actual pts": st.column_config.NumberColumn(format="%.1f"),
            "Scenario pts": st.column_config.NumberColumn(format="%.1f"),
            "Change": st.column_config.NumberColumn(format="%+.1f"),
        })

    with st.container(border=True):
        st.markdown("**Where the scenario still loses points**")
        st.altair_chart(breakdown_chart(b1.reset_index()))

with st.expander("The full scorecard: every band of every factor", icon=":material/table:"):
    t = card.table()
    t["Factor"] = t.feature.map(SHORT)
    t["Band"] = [describe_bin(f, b) for f, b in zip(t.feature, t.bin)]
    st.dataframe(t[["Factor", "Band", "woe", "points"]], hide_index=True, height=420,
                 column_config={"woe": st.column_config.NumberColumn("WoE", format="%.3f"),
                                "points": st.column_config.NumberColumn("Points", format="%.1f")})
    st.caption(f"Score = sum of the ten factors' points. 600 points = 50:1 odds of no loss; every 20 points "
               f"doubles the odds. Watch threshold: P(loss) ≥ {card.threshold:.1%}.")
