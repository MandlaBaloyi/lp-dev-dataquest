import altair as alt
import pandas as pd
import streamlit as st
from sklearn.metrics import roc_curve

from app.data import (BLUE, INK_2, MUTED, ORANGE, PROVINCES, model_json, national_totals,
                                  read_csv, read_json)
from src.common.paths import MODEL_FRAME


@st.cache_data
def labels_frame():
    return pd.read_csv(MODEL_FRAME, usecols=["year", "split", "province", "loss"])


model = model_json()
m = model["metrics"]
log = read_json("cleaning_log.json")
eda = read_json("eda_numbers.json")
nsc_audit = read_json("data_audit_summary.json")

st.title("How we built it")
st.caption("Open data in, a readable scorecard out, and a check at every step that the numbers aren't "
           "flattering themselves.")

data_tab, matric_tab, target_tab, model_tab, leak_tab, limits_tab = st.tabs(
    [":material/cleaning_services: Data quality", ":material/picture_as_pdf: Matric extraction",
     ":material/flag: Target", ":material/monitoring: Performance",
     ":material/shield: Leakage checks", ":material/warning: Limitations"])

with data_tab:
    left, right = st.columns([3, 2])
    with left.container(border=True):
        st.markdown("**The 2017 snapshot is corrupt**")
        t = national_totals()
        line = alt.Chart(t).mark_line(color=BLUE, strokeWidth=2).encode(
            x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("millions:Q", title="Learners reported (millions)", scale=alt.Scale(domain=[11, 14])))
        dots = alt.Chart(t).mark_circle(size=70).encode(
            x="year:O", y="millions:Q",
            color=alt.Color("status:N", scale=alt.Scale(domain=["Kept", "Dropped (corrupt)"], range=[BLUE, ORANGE]),
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("millions:Q", title="Millions", format=".2f"),
                     alt.Tooltip("status:N", title="")])
        st.altair_chart((line + dots).properties(height=300))
        st.caption(f"National enrolment falls from {eda['national_learners_2016_2017_2018_m'][0]}M to "
                   f"{eda['national_learners_2016_2017_2018_m'][1]}M and recovers the next year. In 2017, "
                   f"{eda['share_jump_30pct_2017']:.0%} of schools moved more than 30%, against a typical "
                   f"{eda['share_jump_30pct_typical']:.1%}. A decline-based target would have flagged "
                   "thousands of schools that lost nobody.")
    with right.container(border=True):
        st.markdown("**Defects found and fixed**")
        fixes = pd.DataFrame([
            ("Corrupt 2017 snapshot dropped", log["D1_rows_2017_dropped"]),
            ("Latitude/longitude swapped", log["D4_latlon_swapped"]),
            ("Coordinates rescaled or dropped", log["D4_lat_rescaled_or_dropped"]),
            ("Educators missing, all of 2014", log["D2_educators_missing_2014"]),
            ("MP districts 'NOT APPLICABLE'", log["D7_district_not_applicable"]),
            ("WC 2021 sector column shifted", log["D5_sector_shifted_to_missing"]),
            ("'Combined' schools that were primary", log["D9_combined_excluded_ever_primary"]),
            ("Implausible educator counts", log["D2_educators_implausible_ler"]),
            ("Isolated one-year spikes", log["D3_learner_spikes_to_missing"]),
            ("Open schools with 0 learners", log["D2_learners_zero_to_missing"]),
        ], columns=["Defect", "Rows or schools"])
        st.dataframe(fixes, hide_index=True, column_config={
            "Rows or schools": st.column_config.NumberColumn(format="%d")})
        st.caption(f"{log['rows_in']:,} raw rows → {log['rows_out']:,} clean rows for "
                   f"{log['schools_out']:,} secondary and combined schools. Every rule is in "
                   "docs/CLEANING_DECISIONS.md.")


with matric_tab:
    st.markdown("**The second dataset is not published as a table**")
    st.markdown(
        "Enrolment comes as spreadsheets. Matric results do not — they are printed inside 13 "
        "PDF reports, and no two editions share a column layout. The 2012 edition prints three "
        "years of wrote, achieved and pass rate. The 2021 edition prints five years of progressed "
        "and wrote. One file contains both."
    )

    a, b, c = st.columns(3)
    a.metric("Reports parsed", "13", "2012–2024",
             delta_color="off", delta_arrow="off", border=True)
    b.metric("Records extracted", f"{nsc_audit['matric_records']:,}",
             "school-year results", delta_color="off", delta_arrow="off", border=True)
    c.metric("Layouts encountered", "4", "1, 2, 3 and 4 measures per year",
             delta_color="off", delta_arrow="off", border=True)

    st.markdown("**We got it wrong first, and the audit caught it**")
    st.error(
        "An early parser trusted each report's header as the layout for the whole file. Where a "
        "file mixed layouts, every field shifted. The result passed every row count: 14,005 "
        "records claimed more learners were advanced into matric than sat the exam, 87,055 "
        "carried a quintile outside 1–5, and the pass-rate column extracted at 0% — which looked "
        "so much like a field the source does not publish that it was removed from the model with "
        "a comment explaining why. The comment was wrong and the evidence behind it was our own bug."
    )
    st.success(
        "**The check that settles it.** Where a report prints both the achieved count and the "
        "pass rate, the arithmetic must agree — the rate is achieved ÷ wrote. A misaligned row "
        "cannot satisfy that by chance. After the fix it holds on **82,979 of 82,979 checkable "
        "records**, and pass rate went from unusable to the strongest single variable in the model."
    )

    st.markdown("**What changed**")
    st.dataframe(
        pd.DataFrame([
            ("Records extracted", "71,291", "93,846"),
            ("Progressed exceeds wrote (impossible)", "14,005", "0"),
            ("Quintile outside 1–5 or 99", "87,055", "0"),
            ("Achievement figure present", "7.6%", "88.4%"),
            ("Pass rate present", "0.0%", "88.4%"),
        ], columns=["", "Before the fix", "After"]),
        hide_index=True, width="stretch")

    st.caption(
        "Fewer records, all of them correct. The rows that disappeared are the ones that were "
        "being published as data while being misread."
    )

with target_tab:
    st.markdown(
        "The masterlist gives **total learners per school** and no grade breakdown, so dropout can't be "
        "counted. The target is the closest honest proxy:\n\n"
        "> A school is flagged when its enrolment change over the next **two years** is at least "
        "**15 percentage points worse** than the median school in its province. Only schools with "
        "100 or more learners are labelled.\n\n"
        "Measuring against the province removes province-wide publication artefacts and migration "
        "between provinces, which a school-level intervention can't act on.")
    frame = labels_frame()
    lab = frame[frame.loss.notna() & frame.split.isin(["train", "valid", "test"])]
    a, b = st.columns(2)
    with a.container(border=True):
        st.markdown("**Loss rate by year**")
        by_year = lab.groupby(["year", "split"]).loss.mean().reset_index()
        by_year["split"] = by_year.split.map({"train": "Train", "valid": "Validation", "test": "Test"})
        st.altair_chart(alt.Chart(by_year).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("loss:Q", title="Share of school-years", axis=alt.Axis(format="%")),
            color=alt.Color("split:N", scale=alt.Scale(domain=["Train", "Validation", "Test"],
                                                       range=[BLUE, MUTED, ORANGE]),
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=[alt.Tooltip("year:O"), alt.Tooltip("split:N"), alt.Tooltip("loss:Q", format=".1%")],
        ).properties(height=280))
        st.caption("Stable at 11–16% after the provincial adjustment. 2015 has no label because its "
                   "outcome year is the dropped 2017.")
    with b.container(border=True):
        st.markdown("**Loss rate by province**")
        by_prov = lab.groupby("province").loss.mean().reset_index()
        by_prov["name"] = by_prov.province.map(PROVINCES)
        st.altair_chart(alt.Chart(by_prov).mark_bar(color=BLUE, cornerRadiusEnd=4, height=18).encode(
            y=alt.Y("name:N", sort="-x", title=None),
            x=alt.X("loss:Q", title="Share of school-years", axis=alt.Axis(format="%")),
            tooltip=[alt.Tooltip("name:N", title="Province"), alt.Tooltip("loss:Q", format=".1%")],
        ).properties(height=280))
        st.caption(f"A flagged school loses a median {abs(eda['median_chg_t2_of_losers']):.0%} of its learners. "
                   f"Losses repeat: {eda['p_loss_t2_given_loss_t']:.0%} chance of another one two years later, "
                   f"against {eda['p_loss_t2_given_no_loss_t']:.0%} otherwise.")

with model_tab:
    st.markdown("Trained on **2008–2016**, threshold chosen on **2018–2019**, tested on **2021–2023**. "
                "WoE bins were fitted on training years only and never refitted.")
    rows = []
    for split, name in (("valid", "Validation 2018–19"), ("test", "Test 2021–23")):
        for mdl, mname in (("scorecard", "Scorecard"), ("tree", "Tree benchmark")):
            r = m[f"{mdl}_{split}"]
            rows.append({"Model": mname, "Years": name, "AUC": r["auc"], "Gini": r["gini"], "KS": r["ks"],
                         "Recall": r["recall"], "Precision": r["precision"], "F1": r["f1"],
                         "Accuracy": r["accuracy"], "Worst-10% loss rate": r["top10_precision"],
                         "Lift": r["top10_lift"]})
    perf = pd.DataFrame(rows)
    st.dataframe(perf, hide_index=True, column_config={
        c: st.column_config.NumberColumn(format="%.3f") for c in ["AUC", "Gini", "KS", "Recall", "Precision", "F1", "Accuracy"]
    } | {"Worst-10% loss rate": st.column_config.NumberColumn(format="percent"),
         "Lift": st.column_config.NumberColumn(format="%.2f×")})
    st.caption(f"Accuracy is shown but not led with: predicting that no school loses learners scores "
               f"{m['scorecard_test']['accuracy_all_negative']:.3f}. The threshold targets recall (70% on validation, "
               f"{m['scorecard_test']['recall']:.0%} on test) because a missed school costs more than a wasted visit.")

    a, b, c = st.columns(3)
    with a.container(border=True):
        st.markdown("**ROC, test years**")
        ts = read_csv("test_scores.csv")
        curves = []
        for col, name in (("p", "Scorecard"), ("p_tree", "Tree benchmark")):
            fpr, tpr, _ = roc_curve(ts.loss, ts[col])
            step = max(1, len(fpr) // 400)
            curves.append(pd.DataFrame({"fpr": fpr[::step], "tpr": tpr[::step], "model": name}))
        roc = pd.concat(curves)
        chart = alt.Chart(roc).mark_line(strokeWidth=2).encode(
            x=alt.X("fpr:Q", title="False positive rate"), y=alt.Y("tpr:Q", title="True positive rate"),
            color=alt.Color("model:N", scale=alt.Scale(domain=["Scorecard", "Tree benchmark"], range=[BLUE, ORANGE]),
                            legend=alt.Legend(title=None, orient="bottom")))
        diag = alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(color=MUTED, strokeDash=[4, 4]).encode(x="x", y="y")
        st.altair_chart((chart + diag).properties(height=280))
        st.caption(f"AUC {m['scorecard_test']['auc']:.3f} vs {m['tree_test']['auc']:.3f}: level, so the readable model wins.")
    with b.container(border=True):
        st.markdown("**Stability by year**")
        by = read_csv("auc_by_year.csv").melt(id_vars=["year"], value_vars=["scorecard_auc", "tree_auc"],
                                              var_name="model", value_name="auc")
        by["model"] = by.model.map({"scorecard_auc": "Scorecard", "tree_auc": "Tree benchmark"})
        st.altair_chart(alt.Chart(by).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("auc:Q", title="AUC", scale=alt.Scale(domain=[0.6, 0.72])),
            color=alt.Color("model:N", scale=alt.Scale(domain=["Scorecard", "Tree benchmark"], range=[BLUE, ORANGE]),
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=["year:O", "model:N", alt.Tooltip("auc:Q", format=".3f")],
        ).properties(height=280))
        st.caption(f"Score drift (PSI): {model['psi_score_train_vs_test']:.2f} train→test, "
                   f"{model['psi_score_train_vs_2025']:.2f} train→2025. Both are under the 0.1 warning level.")
    with c.container(border=True):
        st.markdown("**Information Value (training years)**")
        iv = read_csv("iv.csv")
        iv["Status"] = iv.in_model.map({True: "In scorecard", False: "Left out"})
        st.altair_chart(alt.Chart(iv).mark_bar(cornerRadiusEnd=3, height=10).encode(
            y=alt.Y("description:N", sort="-x", title=None, axis=alt.Axis(labelLimit=170)),
            x=alt.X("iv_train:Q", title="IV"),
            color=alt.Color("Status:N", scale=alt.Scale(domain=["In scorecard", "Left out"], range=[BLUE, MUTED]),
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=[alt.Tooltip("description:N", title="Variable"), alt.Tooltip("iv_train:Q", format=".3f", title="IV train"),
                     alt.Tooltip("iv_valid:Q", format=".3f", title="IV valid"), alt.Tooltip("selection_note:N", title="Note")],
        ).properties(height=280))
        st.caption("Selection: IV ≥ 0.02, drop the weaker of any pair correlated above 0.7, "
                   "drop variables whose coefficient reverses sign.")

with leak_tab:
    st.markdown("The brief names two mistakes that inflate scores without raising an error. "
                "We measured both on this data.")
    lk = model["leakage_checks"]
    checks = pd.DataFrame([
        ("Scorecard, split by year (what we report)", m["scorecard_test"]["auc"], "Honest"),
        ("Scorecard, random 70/30 split", lk["scorecard_random_split_auc"], "Barely moves: coarse bins can't memorise schools"),
        ("Tree with school location, split by year", lk["tree_with_location_year_split_auc"], "Honest"),
        ("Tree with school location, random split", lk["tree_with_location_random_split_auc"], "Inflated: the tree recognises schools it saw in other years"),
        ("Scorecard, WoE bins fitted on all years", lk["scorecard_bins_fitted_on_all_data_test_auc"], "Inflated: the bins have seen the test set"),
    ], columns=["Setup", "Test AUC", "Verdict"])
    chart = alt.Chart(checks).mark_bar(cornerRadiusEnd=4, height=18).encode(
        y=alt.Y("Setup:N", sort=None, title=None, axis=alt.Axis(labelLimit=320)),
        x=alt.X("Test AUC:Q", scale=alt.Scale(domain=[0.6, 0.72])),
        color=alt.condition(alt.FieldOneOfPredicate("Verdict", ["Honest"]), alt.value(BLUE), alt.value(ORANGE)),
        tooltip=["Setup", alt.Tooltip("Test AUC:Q", format=".3f"), "Verdict"],
    )
    text = chart.mark_text(align="left", dx=4, color=INK_2).encode(text=alt.Text("Test AUC:Q", format=".3f"))
    with st.container(border=True):
        st.altair_chart((chart + text).properties(height=230))
    st.dataframe(checks, hide_index=True, column_config={"Test AUC": st.column_config.NumberColumn(format="%.3f")})
    st.caption("Four tests in tests/test_pipeline.py pin these guards: splits never overlap in time, bins stay frozen "
               "after fitting, features never read a later year, and the saved scorecard reproduces the "
               "published ranking.")

with limits_tab:
    st.markdown(
        """
1. **This measures learner loss, not dropout.** A school losing learners to a better school nearby
   looks the same as one losing them from the system. Grade-level counts would separate the two.
2. **Small schools rank high partly for arithmetic reasons.** Losing a few learners is a bigger
   percentage of a small school. A size-scaled threshold would reorder the list.
3. **Adjusting for the province is a judgement call.** Without it, the Eastern Cape dominates the list.
4. **2017 was dropped, not repaired.** Recovering it would add a training year.
5. **Schools that vanish are left unlabelled** (1,604 school-years): a missing row is as likely to be an
   EMIS renumbering as a closure.
6. **Northern Cape isn't ranked for 2025.** Its 2025 masterlist was not published.
7. **Modest power (AUC ≈ 0.65).** This is a triage list for deciding where to look first, not a verdict.
   The biggest likely gain is NSC Grade 12 entries per school as an end-of-cohort count.
        """
    )
    st.info("The scorecard's factors (size, volatility, recent change, share of peak, quintile, province, "
            "district context) are all visible in the public masterlist. Any official can check a school's "
            "score by hand.", icon=":material/visibility:")
