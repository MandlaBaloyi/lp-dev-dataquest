"""The final model, reported in full.

Everything a risk model should be judged on, not AUC alone. AUC scores a whole
ranking; nobody works a whole ranking. A district works the top of it with the
staff it has, so the decile table and the confusion matrix decide whether this
is usable and AUC only describes it.

Every figure here is measured on 2021-2023 - years the model never saw during
training or tuning.
"""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from app.data import BLUE, MUTED, ORANGE, model_json, out, read_json
from src.model import evaluate

model = model_json()
metrics = model["metrics"]
test = metrics["scorecard_test"]
tree = metrics["tree_test"]
checks = model["leakage_checks"]


@st.cache_data
def scores():
    return pd.read_csv(out("test_scores.csv"))


@st.cache_data
def forest():
    """The random forest benchmark, trained on the same frame and split."""
    import json
    import os
    path = out("forest_metrics.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


st.title("The final model")
st.markdown(
    f"A **Logistic Regression Scorecard** over **{len(model['features_in_model'])} variables**, "
    "trained on 2008–2016, tuned on 2018–2019 and measured once on **2021–2023**. "
    "Every number below comes from those test years, which the model never saw."
)
st.caption(
    "**The algorithm is logistic regression.** \"Scorecard\" describes how its "
    "coefficients are presented: each variable is cut into bands, each band is "
    "encoded by its Weight of Evidence, and the fitted coefficients are scaled into "
    f"points — {model['scaling']['pdo']} points doubles the odds, and "
    f"{model['scaling']['base_score']} is {model['scaling']['base_odds_good_to_bad']}:1 "
    "odds of no loss. It is the standard construction behind a credit score, and it is "
    "what lets the register tell a school it lost 37 points for its matric pass rate "
    "rather than just handing it a number."
)

with st.container(horizontal=True):
    st.metric("AUC", f"{test['auc']:.3f}", f"Gini {test['gini']:.3f}",
              delta_color="off", delta_arrow="off", border=True,
              help="Pick one at-risk school and one healthy school at random. "
                   "AUC is how often the model scores the at-risk one higher.")
    st.metric("KS", f"{test['ks']:.3f}", "separation of the two score distributions",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Recall", f"{test['recall']:.0%}", "of real losses, caught",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Lift, worst tenth", f"{test['top10_lift']:.2f}×",
              f"{test['top10_precision']:.1%} loss rate vs {test['event_rate']:.1%} base",
              delta_color="off", delta_arrow="off", border=True)

st.divider()
st.subheader("Confusion matrix")
st.caption(
    f"At the operating threshold, on {test['n']:,} school-years in 2021–2023. "
    f"{test['event_rate']:.1%} of them really did lose learners."
)

# Computed from the actual predictions rather than back-derived from rounded
# metrics, and through the same evaluation module the pipeline uses - so the
# matrix on screen is the one the model really produced.
predictions = scores()
counts = evaluate.confusion(
    predictions["loss"], predictions["p"] >= model["threshold_scorecard_prob"])
true_positive = counts["true_positive"]
false_negative = counts["false_negative"]
false_positive = counts["false_positive"]
true_negative = counts["true_negative"]

matrix = evaluate.confusion_frame(
    predictions["loss"], predictions["p"] >= model["threshold_scorecard_prob"])
matrix.index = ["Actually stable", "Actually lost learners"]
matrix.columns = ["Predicted stable", "Predicted at risk"]

left, right = st.columns([2, 3])
with left:
    st.dataframe(matrix, use_container_width=True)
with right:
    st.markdown(
        f"- **{true_positive:,} caught.** Schools that really lost learners and were flagged.\n"
        f"- **{false_negative:,} missed.** The costly error — a school losing learners that "
        "nobody was sent to.\n"
        f"- **{false_positive:,} false alarms.** A visit to a school that turned out fine. "
        "Cheap by comparison.\n"
        f"- **{true_negative:,} correctly left alone.**"
    )
    st.caption(
        "The threshold favours recall deliberately. A missed school gets nothing; a wrongly "
        "flagged one gets support it needed slightly less than predicted. Those costs are not "
        "symmetric, so the cut is not set where accuracy peaks."
    )

st.divider()
st.subheader("Every metric, and what each one is for")

rows = [
    ("AUC", f"{test['auc']:.4f}", "Ranking quality across the whole list."),
    ("Gini", f"{test['gini']:.4f}", "The same information as AUC, in the form scorecards are usually quoted in: 2×AUC − 1."),
    ("KS", f"{test['ks']:.4f}", "The widest gap between the score distributions of schools that lost learners and those that did not."),
    ("Recall", f"{test['recall']:.4f}", "Of the schools that really lost learners, the share we flagged."),
    ("Precision", f"{test['precision']:.4f}", "Of the schools we flagged, the share that really lost learners. Against a base rate of 12.2%."),
    ("F1", f"{test['f1']:.4f}", "The balance of precision and recall in one number."),
    ("Accuracy", f"{test['accuracy']:.4f}", "Reported, not led with — see the warning below."),
    ("Lift, worst tenth", f"{test['top10_lift']:.3f}×", "How much more often the worst-scored tenth loses learners than a school picked at random. The number a planner actually uses."),
    ("Flagged share", f"{test['flagged_share']:.1%}", "How much of the country the threshold puts on the list."),
]
st.dataframe(pd.DataFrame(rows, columns=["Metric", "Value", "What it tells you"]),
             hide_index=True, use_container_width=True,
             column_config={"Metric": st.column_config.TextColumn(width="small"),
                            "Value": st.column_config.TextColumn(width="small"),
                            "What it tells you": st.column_config.TextColumn(width="large")})

st.warning(
    f"**Accuracy is the weakest number here and we are not hiding it.** At "
    f"{test['accuracy']:.1%} it is below the {test['accuracy_all_negative']:.1%} you would score "
    "by predicting that no school ever loses learners — a model that identifies nobody. That is "
    "the arithmetic of an imbalanced problem, and it is exactly why accuracy is the wrong headline "
    "and lift is the right one."
)

st.divider()
st.subheader("Where the losses sit in the ranking")

decile_table = evaluate.deciles(predictions["loss"], predictions["p"])
deciles = list(decile_table["loss_rate"])
frame = pd.DataFrame({"decile": decile_table.index, "loss_rate": deciles})
frame["label"] = frame["decile"].map(lambda d: f"{d}")

bars = alt.Chart(frame).mark_bar().encode(
    x=alt.X("label:N", title="Risk decile  (1 = highest risk)", sort=None),
    y=alt.Y("loss_rate:Q", title="Share that lost learners", axis=alt.Axis(format="%")),
    color=alt.condition(alt.datum.decile <= 1, alt.value(ORANGE), alt.value(BLUE)),
    tooltip=[alt.Tooltip("decile:O", title="Decile"),
             alt.Tooltip("loss_rate:Q", format=".1%", title="Loss rate")])
base_line = alt.Chart(pd.DataFrame({"y": [test["event_rate"]]})).mark_rule(
    strokeDash=[6, 4], color=MUTED).encode(y="y:Q")
st.altair_chart(bars + base_line, use_container_width=True)

st.success(
    f"**The worst-scored tenth loses learners {deciles[0]:.1%} of the time against "
    f"{deciles[-1]:.1%} in the best-scored tenth** — roughly a "
    f"{deciles[0] / max(deciles[-1], 0.001):.0f}-fold separation. The dashed line is the national "
    f"base rate of {test['event_rate']:.1%}. Working the top of this list is about twice as "
    "productive as working at random, and that is the whole product."
)

st.divider()
st.subheader("Interpretable model versus the benchmark")

rf = forest()
rows = [("Scorecard — shipped", test["auc"], test["gini"], test["ks"],
         "Yes — every score breaks into visible points"),
        ("Gradient-boosted tree", tree["auc"], tree["gini"], tree["ks"],
         "No — no per-school explanation")]
if rf:
    rows.append(("Random forest, calibrated", rf["auc"], rf["gini"], rf["ks"],
                 "No — ranks well, explains nothing"))

comparison = pd.DataFrame(rows, columns=["Model", "AUC", "Gini", "KS", "Explains itself?"])
st.dataframe(comparison, hide_index=True, use_container_width=True,
             column_config={"AUC": st.column_config.NumberColumn(format="%.4f"),
                            "Gini": st.column_config.NumberColumn(format="%.4f"),
                            "KS": st.column_config.NumberColumn(format="%.4f")})

if rf:
    gap = rf["auc"] - test["auc"]
    st.markdown(
        f"The forest reaches **{rf['auc']:.4f}** against the scorecard's **{test['auc']:.4f}** — "
        f"a gap of **{gap:+.4f}**, with a lift of **{rf['top10_lift']:.2f}×** in the worst tenth. "
        "It is the better ranker and it is not what ships."
    )
    st.info(
        "**Why the weaker model is the one delivered.** The output of this system directs "
        "public money. An official who is told a school is high-risk will be asked why, and "
        "\"the forest said so\" does not survive that question — it cannot be checked against "
        "the masterlist, appealed by the school, or defended to a treasury. The scorecard gives "
        f"up {abs(gap):.3f} AUC and returns three named reasons per school in exchange.\n\n"
        "The forest is kept as the honest measure of what that choice costs. Reporting only the "
        "model we shipped would hide the trade-off rather than make it."
    )
else:
    st.markdown(
        f"The tree scores **{tree['auc'] - test['auc']:+.4f} AUC** against the scorecard. That is "
        "the price of interpretability, and it is small enough to pay."
    )

st.divider()
st.subheader("Two mistakes we measured rather than asserted")

a, b = st.columns(2)
with a.container(border=True, height="stretch"):
    st.markdown(":material/shuffle: **Splitting the data at random**")
    st.markdown(
        f"A tree that can see a school's location scores **{checks['tree_with_location_random_split_auc']:.4f}** "
        f"under a random split and **{checks['tree_with_location_year_split_auc']:.4f}** under a split by year — "
        f"an inflation of **{checks['tree_with_location_random_split_auc'] - checks['tree_with_location_year_split_auc']:+.4f}**."
    )
    st.caption(
        "A school appears in up to sixteen rows, one per year. Split at random and the same school "
        "trains and tests the model, which then scores well by recognising it rather than by "
        "learning anything transferable. Nothing errors. We split by year."
    )
with b.container(border=True, height="stretch"):
    st.markdown(":material/content_cut: **Fitting the bins on all the data**")
    st.markdown(
        f"Bins fitted across every year score **{checks['scorecard_bins_fitted_on_all_data_test_auc']:.4f}** "
        f"against **{test['auc']:.4f}** when fitted on training years alone — "
        f"**{checks['scorecard_bins_fitted_on_all_data_test_auc'] - test['auc']:+.4f}** of borrowed credit."
    )
    st.caption(
        "Weight of Evidence bins learned across all years have already seen the test set. The "
        "metrics come back better and the model is no better. Ours are fitted on training years "
        "and applied unchanged."
    )

st.divider()
st.subheader("Is it still the same population?")

psi_test = model["psi_score_train_vs_test"]
psi_2025 = model["psi_score_train_vs_2025"]
c1, c2 = st.columns(2)
c1.metric("PSI, training vs test", f"{psi_test:.3f}",
          "stable" if psi_test < 0.1 else "drifting",
          delta_color="off", delta_arrow="off", border=True)
c2.metric("PSI, training vs 2025", f"{psi_2025:.3f}",
          "stable" if psi_2025 < 0.1 else "drifting",
          delta_color="off", delta_arrow="off", border=True)
st.caption(
    "Population Stability Index compares the distribution of scores between periods. Below 0.1 "
    "means the schools being scored today still look like the schools the model was trained on — "
    "which is what makes it safe to keep using without retraining."
)

st.divider()
st.subheader("What this model is not")

st.error(
    "**It is a triage list, not a verdict.** At an AUC of "
    f"{test['auc']:.3f} the ranking is worth working from the top of, and it is not good enough "
    "to be believed about any single school without a visit.\n\n"
    "**It measures enrolment decline, not dropout.** A learner who transfers to a better school "
    "and one who leaves education entirely look identical in a headcount. The honest claim is "
    "that these schools are shedding learners faster than their province, not that those learners "
    "have left the system.\n\n"
    "**Whole-school enrolment is a coarse instrument.** Per-grade counts sit in a dataset held "
    "under separate permission. With them, this becomes a measure of Grade 10–12 attrition "
    "specifically rather than of a school shrinking."
)
