"""EDA and evaluation charts for REPORT.md. Run after train.

    python -m independent.src.charts
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve

from independent.src.paths import MODEL_FRAME, RAW_PANEL, out

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
MUTED = "#b9b8b2"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(out(name), dpi=150)
    plt.close(fig)


def bars(ax, labels, values, colors, fmt="{:.0%}"):
    x = np.arange(len(labels))
    ax.bar(x, values, color=colors, width=0.7, edgecolor=SURFACE, linewidth=2)
    ax.set_xticks(x, labels)
    for xi, v in zip(x, values):
        ax.text(xi, v, fmt.format(v), ha="center", va="bottom", fontsize=8, color=INK_2)
    ax.grid(axis="x", visible=False)


def legend(ax, items, loc="upper right"):
    handles = [matplotlib.patches.Patch(color=c, label=l) for c, l in items]
    ax.legend(handles=handles, frameon=False, loc=loc, fontsize=8)


def raw_findings(numbers):
    raw = pd.read_csv(RAW_PANEL, usecols=["emis", "year", "learners"], low_memory=False)
    raw["L"] = pd.to_numeric(raw.learners, errors="coerce")
    tot = raw.groupby("year").L.sum() / 1e6
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(tot.index, tot.values, color=BLUE, lw=2, marker="o", ms=4)
    ax.plot([2017], [tot[2017]], marker="o", ms=9, color=ORANGE, zorder=3)
    ax.annotate(f"2017: {tot[2017]:.1f}M\n(snapshot dropped)", (2017, tot[2017]), xytext=(2012.2, 11.6),
                color=INK_2, fontsize=9, arrowprops=dict(arrowstyle="-", color=INK_2, lw=0.8))
    ax.set_title("Learners reported nationally, all schools (millions)")
    ax.set_xticks(tot.index[::2])
    ax.set_ylim(11, 14)
    save(fig, "fig1_national_enrolment.png")
    numbers["national_learners_2016_2017_2018_m"] = [round(tot[y], 2) for y in (2016, 2017, 2018)]

    raw = raw.sort_values(["emis", "year"])
    raw["Lp"] = raw.groupby("emis").L.shift()
    raw["yp"] = raw.groupby("emis").year.shift()
    c = raw[(raw.yp == raw.year - 1) & (raw.Lp >= 50)]
    jump = (c.L / c.Lp - 1).abs().gt(0.3).groupby(c.year).mean()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    colors = [ORANGE if y in (2017, 2018) else BLUE for y in jump.index]
    bars(ax, [str(y)[2:] for y in jump.index], jump.values, colors)
    ax.set_title("Schools whose enrolment moved more than 30% in one year")
    ax.set_xlabel("year (20xx)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
    save(fig, "fig2_one_year_jumps.png")
    numbers["share_jump_30pct_typical"] = round(float(jump.drop([2017, 2018]).median()), 3)
    numbers["share_jump_30pct_2017"] = round(float(jump[2017]), 3)


def target_findings(numbers):
    df = pd.read_csv(MODEL_FRAME)
    lab = df[df.loss.notna() & df.split.isin(["train", "valid", "test"])]

    by_year = lab.groupby("year").loss.mean()
    fig, ax = plt.subplots(figsize=(8, 3.2))
    colors = [{"train": BLUE, "valid": MUTED, "test": ORANGE}[lab[lab.year == y].split.iat[0]] for y in by_year.index]
    bars(ax, [str(y) for y in by_year.index], by_year.values, colors)
    ax.set_title("Share of school-years that lost learners")
    legend(ax, [(BLUE, "train"), (MUTED, "validation"), (ORANGE, "test")])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
    save(fig, "fig3_target_by_year.png")

    by_prov = lab.groupby("province").loss.mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 3.2))
    bars(ax, by_prov.index, by_prov.values, BLUE)
    ax.set_title("Share of school-years that lost learners, by province")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
    save(fig, "fig4_target_by_province.png")
    numbers["loss_rate_by_province"] = by_prov.round(3).to_dict()

    train = lab[lab.split == "train"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    size = train.groupby(pd.qcut(train.learners, 5), observed=True).loss.mean()
    bars(axes[0], [f"{int(i.left)}-{int(i.right)}" for i in size.index], size.values, BLUE)
    axes[0].set_title("by school size (learners)")
    axes[0].tick_params(axis="x", labelsize=7)
    vol = train.groupby(pd.qcut(train.vol, 5), observed=True).loss.mean()
    bars(axes[1], ["lowest", "", "", "", "highest"], vol.values, BLUE)
    axes[1].set_title("by enrolment volatility")
    chg = train.groupby(pd.qcut(train.chg1, 7), observed=True).loss.mean()
    bars(axes[2], [f"{i.right:+.0%}" if k < 6 else "more" for k, i in enumerate(chg.index)], chg.values, BLUE)
    axes[2].set_title("by last year's change (upper edge)")
    axes[2].tick_params(axis="x", labelsize=7)
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
    fig.suptitle("Loss rate in the training years", x=0.01, ha="left", fontweight="bold")
    save(fig, "fig5_drivers.png")
    numbers["loss_rate_by_size_quintile"] = size.round(3).tolist()
    numbers["loss_rate_by_vol_quintile"] = vol.round(3).tolist()
    numbers["loss_rate_by_chg1_septile"] = chg.round(3).tolist()

    # The target in plain numbers
    numbers["labelled_rows"] = int(len(lab))
    numbers["loss_rate_overall"] = round(float(lab.loss.mean()), 3)
    numbers["median_chg_t2_of_losers"] = round(float(lab[lab.loss == 1].chg_t2.median()), 3)
    numbers["median_learners_lost_by_losers"] = round(float(
        (lab[lab.loss == 1].learners - lab[lab.loss == 1].learners_t2).median()), 0)
    numbers["closed_or_renumbered_by_t2"] = int(df.closed_by_t2.sum())
    numbers["schools_loss_in_3plus_years"] = int((lab.groupby("emis").loss.sum() >= 3).sum())
    numbers["schools_labelled"] = int(lab.emis.nunique())
    # Persistence: does a loss predict the next window's loss?
    nxt = lab.set_index(["emis", "year"]).loss
    later = nxt.reindex(pd.MultiIndex.from_arrays([lab.emis, lab.year + 2])).to_numpy()
    m = ~np.isnan(later)
    pers = pd.Series(later[m]).groupby(lab.loss.to_numpy()[m]).mean()
    numbers["p_loss_t2_given_loss_t"] = round(float(pers.get(1.0)), 3)
    numbers["p_loss_t2_given_no_loss_t"] = round(float(pers.get(0.0)), 3)


def model_charts(numbers):
    iv = pd.read_csv(out("iv.csv")).sort_values("iv_train")
    fig, ax = plt.subplots(figsize=(8, 5.2))
    colors = [BLUE if k else MUTED for k in iv.in_model]
    ax.barh(iv.description, iv.iv_train, color=colors, height=0.7, edgecolor=SURFACE, linewidth=2)
    ax.axvline(0.02, color=INK_2, lw=0.8, ls="--")
    ax.text(0.021, len(iv) - 0.4, "0.02 floor", color=INK_2, fontsize=8)
    for y, v in enumerate(iv.iv_train):
        ax.text(v + 0.002, y, f"{v:.3f}", va="center", fontsize=8, color=INK_2)
    ax.set_title("Information Value, training years")
    legend(ax, [(BLUE, "in the scorecard"), (MUTED, "left out")], loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, "fig6_information_value.png")

    ts = pd.read_csv(out("test_scores.csv"))
    fig, ax = plt.subplots(figsize=(4.8, 4.6))
    for col, colr, name in (("p", BLUE, "Scorecard"), ("p_tree", ORANGE, "Tree benchmark")):
        fpr, tpr, _ = roc_curve(ts.loss, ts[col])
        ax.plot(fpr, tpr, color=colr, lw=2, label=name)
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--")
    m = json.load(open(out("model.json")))["metrics"]
    ax.set_title(f"ROC, test years 2021-2023")
    ax.text(0.45, 0.12, f"Scorecard AUC {m['scorecard_test']['auc']:.3f}\nTree AUC {m['tree_test']['auc']:.3f}",
            color=INK_2, fontsize=9)
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig7_roc_test.png")

    ts["decile"] = pd.qcut(ts.score.rank(method="first"), 10, labels=range(1, 11))
    dec = ts.groupby("decile", observed=True).loss.mean()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    bars(ax, [str(d) for d in dec.index], dec.values, [ORANGE] + [BLUE] * 9)
    ax.axhline(ts.loss.mean(), color=INK_2, lw=0.8, ls="--")
    ax.text(9.4, ts.loss.mean() + 0.004, "average", color=INK_2, fontsize=8, ha="right")
    ax.set_title("Loss rate by scorecard decile, test years (1 = lowest score, highest risk)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
    save(fig, "fig8_decile_lift_test.png")
    numbers["test_loss_rate_by_decile"] = dec.round(3).tolist()

    rank = pd.read_csv(out("ranking_2025.csv"))
    numbers["ranking_2025_rows"] = int(len(rank))
    numbers["ranking_2025_tiers"] = rank.tier.fillna("").value_counts().to_dict()
    numbers["ranking_2025_priority_by_province"] = (
        rank[rank.tier == "PRIORITY"].province.value_counts().to_dict())


def main():
    numbers = {}
    raw_findings(numbers)
    target_findings(numbers)
    model_charts(numbers)
    with open(out("eda_numbers.json"), "w") as fh:
        json.dump(numbers, fh, indent=2, default=float)
    print(json.dumps(numbers, indent=2, default=float))


if __name__ == "__main__":
    main()
