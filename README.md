# The Missing List

**A school-level dropout risk register for South Africa.**
DataQuest hackathon · Theme: Education

---

More than 40% of South African learners who start Grade 1 never finish matric.
That figure is published every year and is not in dispute. What does not exist,
anywhere, is the same figure **school by school** — so nobody can point it at
anything. You cannot deploy a teacher to a percentage.

This project builds that list. It audits every school record the country
publishes, repairs what it finds, then scores and ranks every secondary school
on its risk of losing learners — with the reasons attached.

## What it does

| | |
|---|---|
| **Audits** | 7 detectors across 2 datasets and **572,607 records** → 19 findings, 13 severe |
| **Models** | Weight-of-Evidence logistic scorecard, **AUC 0.694** on years it never saw |
| **Ranks** | **7,681 secondary schools** scored for 2025, 842 flagged priority |
| **Explains** | Every score breaks into visible points and three named reasons |

The worst-scored tenth of schools loses learners **26.8%** of the time against
**1.95%** in the best-scored tenth.

## Quick start

```bash
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Opens at http://localhost:8501. The built tables are committed, so nothing
needs downloading first.

> `streamlit` is not on PATH on all machines. `python -m streamlit` always
> works and is the form used throughout.

## Everything you can run

```bash
# the app — nine pages, in the order the argument is made
python -m streamlit run app/streamlit_app.py

# tests
python -m pytest tests/ -v

# rebuild from source (only needed to refresh — outputs are committed)
python -m src.fetch.emis_masterlists   # 234 provincial spreadsheets
python -m src.fetch.nsc_reports        # 13 matric report PDFs
python -m src.build.nsc_results        # PDFs  -> nsc_results.csv
python -m src.build.school_panel       # sheets -> school_year_panel.csv.gz
python -m src.build.clean              #        -> clean_panel.csv.gz
python -m src.model.features           #        -> model_frame.csv.gz
python -m src.model.train              # scorecard + benchmarks -> outputs/
python -m src.model.charts             # figures -> outputs/
```

Everything runs as a module from the repository root. Running a file by path
(`python src/model/train.py`) breaks the `src.` imports.

## Layout

```
app/          the Streamlit application, nine pages
src/
  common/     paths, identifier normalisation, loading
  fetch/      download from the department's own site
  build/      raw files -> clean tables
  eda/        anomaly detection, weight of evidence
  model/      features, scorecard, scoring, evaluation, charts
datasets/
  raw/        gitignored — rebuilt by src/fetch
  processed/  the built tables, committed
outputs/      model artefacts, the register, figures
tests/        59 tests
docs/         problem, datasets, dictionary, methodology, business, security
submission/   presentation materials
```

## Documentation

| File | What it covers |
|---|---|
| `docs/PROBLEM_STATEMENT.txt` | The problem, the solution, what we are honest about |
| `docs/DATASETS.txt` | Sources, how they join, the timing rule, the extraction bug |
| `docs/DATA_DICTIONARY.txt` | Every column, fill rate, and how it is treated |
| `docs/METHODOLOGY.md` | Cleaning, target, model, evaluation |
| `docs/CLEANING_DECISIONS.md` | Every cleaning rule with its row cost |
| `docs/BUSINESS_MODEL.txt` | Who pays, what it costs, how it scales |
| `docs/DEMO_SCRIPT.md` | Seven-minute walkthrough |

## What we are honest about

- **It scores schools, never learners.** Learner records are protected under
  POPIA and are not used. The system holds no personal data by design.
- **It measures enrolment decline, not dropout.** A learner who transfers and
  one who leaves education look identical in a headcount.
- **It is a triage list, not a verdict.** At 0.694 AUC the ranking is worth
  working from the top of, and not good enough to be believed about any single
  school without a visit.
- **Risk is not yet split by grade.** That needs per-grade enrolment, held
  under separate permission. The same pipeline answers it the day that arrives.
- **Our own extraction was one of the things the audit caught.** A parser bug
  corrupted 14,005 matric records and silently destroyed the pass-rate column.
  It is documented rather than quietly fixed.

## Source defects this pipeline corrects

None of these raise an error. Each one silently changes what a model learns.

- **2017 loses 1.44 million learners** nationally and 2018 gains 1.31 million
  back. A publication fault, not demography.
- **Province codes are unstable** — `KZ`/`KZN` and `GT`/`GP` turn a country of
  nine provinces into a dataset of eleven.
- **Gauteng's 2023 file** has its key column headed `"G"`, truncated upstream.
  Three thousand schools vanish.
- **Phase is `Phase_PED` in newer files, `Phase_DoE` in older ones** — and
  phase is how a secondary school is identified at all.
- **724 schools sit at latitude zero**, a point in the Atlantic Ocean.
- **Northern Cape 2025** is a Word template published into the slot where the
  spreadsheet belonged.
