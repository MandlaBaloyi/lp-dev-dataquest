# Early Warning System for School Dropout - South Africa

Predicts, per school, how much of a Grade 10–12 cohort is at risk of being lost
before matric, so districts and NGOs can direct support to the schools most
likely to lose learners — before they leave, rather than counting them after.

About 40% of learners who start Grade 1 in South Africa never reach Grade 12
(DG Murray Trust, Zero Dropout Campaign). Attrition is steepest in Grades 10–12.
No widely deployed tool ranks schools by that risk ahead of time.

## What this repository holds

Open government data, the scripts that fetch and assemble it, and the model
trained on the result. Coverage is **national — all nine provinces, 2007–2025**.

| Table | Rows | What it is |
|---|---|---|
| `datasets/processed/school_year_panel.csv.gz` | 478,761 | Every school, every year |
| `datasets/processed/model_table.csv` | 184,620 | Secondary + combined schools only — the training population (12,433 schools) |
| `datasets/processed/preview_2025.csv` | 8,654 | Latest year, small enough to open directly |

Raw downloads are **not** committed — several hundred MB, all re-downloadable
without a login. `src/fetch/` rebuilds them exactly.

## Quick start

```bash
pip install -r requirements.txt
python -m streamlit run app/Home.py
```



Note: `streamlit` is not on PATH on all machines. `python -m streamlit` always
works and is the form used throughout.

## Everything you can run

```bash
# The EDA app - explore the raw data, make and record cleaning decisions
python -m streamlit run app/Home.py

# Tests - cleaning rules, WoE/IV, and guards on the training table
python -m pytest tests/ -v

# Rebuild the data from source (only needed to refresh; takes a while)
python -m src.fetch.emis_masterlists   # 234 provincial masterlists from DBE
python -m src.fetch.nsc_reports        # 13 NSC School Performance Reports
python -m src.build.school_panel       # -> school_year_panel.csv.gz
python -m src.build.model_table        # -> model_table.csv
```

Every script runs as a module from the repository root. Running them as file
paths (`python src/build/model_table.py`) will fail on the `src.` imports.

## Layout

```
src/common/   paths and EMIS normalisation, shared by everything
src/fetch/    stage 1 - download raw data from DBE
src/build/    stage 2 - raw files into clean tables
src/model/    stage 3 - label, features, training, evaluation
tests/        pins the source defects listed below
datasets/     raw/ (gitignored) and processed/ (committed)
docs/         problem statement, business model, technical plan
outputs/      rankings, charts, trained model
```

## Source defects this pipeline corrects

None of these raise an error. Each one silently skews what a model would learn.

- **2019 files** spell the key column `NatEMIS`, every other year `NatEmis`.
  Exact matching drops the entire year while the panel still looks healthy.
- **Province codes are unstable** — KwaZulu-Natal appears as `KZ` and `KZN`,
  Gauteng as `GT` and `GP`, splitting two provinces into four.
- **Gauteng's 2023 file** has its key column headed `"G"`, truncated upstream.
  Recovered by inspecting values rather than trusting the header.
- **Quintile** is published as `3` in some years and `Q3` in others, plus a
  literal `TO BE UPDATED`. Untouched, a model treats `3` and `Q3` as unrelated.
- **Phase** is `Phase_PED` in recent files and `Phase_DoE` in older ones. Phase
  is what identifies a secondary school, so losing it loses the population this
  project is about.
- **Northern Cape 2025 Q2** on DBE's page is a Word template, not a masterlist.
  NC has no 2025 row. Nothing fixable at our end.

## Documentation

- `docs/problem.txt` — problem, solution, business model
- `docs/plan_v1.txt` — technical plan: features, label, modelling
- `datasets/INDEX.md` — data inventory, source by source
- `independent/` — the second team's independent track (own cleaning, target,
  scorecard, 2025 ranking and presentation app); start at `independent/README.md`.
  Run the app with `python -m streamlit run independent/app/streamlit_app.py`,
  and see `independent/DEMO.md` for the demo script
