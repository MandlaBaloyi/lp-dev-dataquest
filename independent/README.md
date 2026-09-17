# Independent track

The second team's answer to `docs/Independent_Track_Brief.docx`. It was built
from `datasets/processed/school_year_panel.csv.gz` alone, without reading the
primary track's cleaning, target definition or model.

| Deliverable | Where |
|---|---|
| Cleaned dataset | `data/clean_panel.csv.gz` (146,944 rows, 9,157 secondary and combined schools); `data/model_frame.csv.gz` (features and target) |
| Record of every decision | [DECISIONS.md](DECISIONS.md) |
| Problem and solution | [REPORT.md §1–2](REPORT.md) |
| EDA findings | [REPORT.md §4](REPORT.md), with charts in `outputs/fig1`–`fig5` |
| Model, evaluation, explanations | [REPORT.md §5](REPORT.md); `outputs/scorecard.csv`, `iv.csv`, `metrics.csv`, `model.json` |
| Ranked 2025 list with reasons | `outputs/ranking_2025.csv` |
| Interactive app | `app/`, walked through in [DEMO.md](DEMO.md) |
| Backup screenshots | `docs/screenshots/` |

**In one line:** a WoE logistic scorecard ranks schools by the risk of losing
learners faster than their province over the next two years. It scores test
AUC 0.654 (Gini 0.31) on 2021–23, level with a gradient-boosted benchmark at
0.657, so the interpretable model is preferred.

## Run

From the repository root:

```bash
# pipeline, about 3 minutes
python -m independent.src.clean
python -m independent.src.features
python -m independent.src.train
python -m independent.src.charts
python -m pytest independent/tests -v

# app, opens at http://localhost:8501
python -m streamlit run independent/app/streamlit_app.py
```

The app has five pages, laid out as a presentation:

1. **Overview**: the problem, headline numbers, and how it works.
2. **Risk list**: filterable 2025 ranking with a map, reasons, and CSV download.
3. **School profile**: rank, score, points lost per factor, and enrolment history.
4. **Score simulator**: change any factor and watch the score and tier move.
5. **How we built it**: data defects, target, performance, leakage checks, and limitations.

The app computes nothing of its own. It reads `outputs/` and re-scores
schools with the saved scorecard (`src/scoring.py`), and a test checks that
the saved scorecard reproduces the published ranking.

## Layout

```
src/paths.py      file locations
src/clean.py      raw panel -> clean panel (rules D1-D9)
src/features.py   clean panel -> features + target, year splits
src/woe.py        WoE binning and IV, fitted on training years only
src/train.py      scorecard, tree benchmark, metrics, leakage checks, 2025 ranking
src/charts.py     report charts and EDA numbers
src/scoring.py    rebuilds the scorecard from outputs/model.json (used by the app)
app/              Streamlit app: streamlit_app.py, app_pages/, .streamlit/config.toml
tests/            guards: year split, frozen bins, no look-ahead, cleaning rules
```
