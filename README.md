# The Missing List

**A school-level dropout risk register for South Africa.**

<sub>DataQuest hackathon · Theme: Education · Identify data discrepancy and anomaly in education data, and build a data-driven solution</sub>

---

More than **40% of South African learners who start Grade 1 never finish
matric.** Put plainly: 40 of every 100 children who walk into a Grade 1
classroom will not walk out of a Grade 12 one. That figure is published, widely
quoted, and not in dispute.

### So the obvious question is: how do we save those learners?

That is the real problem — and it is not that the number is unknown. It is well
known. It is that **it cannot be pointed at anything.** Nobody can deploy a
teacher to a percentage. An organisation with one retention programme and
funding for twelve schools cannot use a national average to choose the twelve.
Learners are counted after they are gone, in aggregate, once a year.

*Every year that list does not exist, help goes somewhere — just not necessarily
where the loss is worst.*

## Four questions stand in the way

Before *how do we save them* can be answered, four smaller questions have to be.
**None of them currently has an answer anywhere in the public record.** This
register answers three.

| Question | What the 2025 register delivers | |
|---|---|---|
| Which provinces are losing the most? | 8 of 9, ranked by measured risk rather than estimate | ✅ |
| Which districts inside those provinces? | 72, ranked within their province | ✅ |
| Which schools inside those districts? | **7,681** secondary and combined schools, scored individually | ✅ |
| Which grades inside those schools? | Needs per-grade enrolment, held under separate permission | ⏳ |

**Why 8 provinces and not 9.** Northern Cape published a Word template into the
slot where its 2025 masterlist belonged, so it has no 2025 data to score — a
fault our own audit found, not one we introduced. The model covers all nine; the
register covers the eight that published.

**On the fourth question we are deliberate.** We can say a school is losing its
Grade 8–12 pipeline. We cannot yet say whether the loss concentrates in Grade 10
or Grade 11. That is a form, not a rebuild — the same pipeline answers it the
day the permission arrives.

## We build the missing list

Using **19 years of open government data** covering every school in all nine
provinces, we score each secondary school on its risk of losing learners before
matric, rank them worst first, and attach the reasons.

| | |
|---|---|
| **Schools scored for 2025** | **7,681** — secondary & combined, 100+ learners |
| **Priority tier** | **842** — the worst 10% of scores |
| **Loss rate, highest-risk tenth** | **28.5%** against 2.4% in the lowest-risk tenth |
| **Test AUC** | **0.694** · Gini 0.388 · KS 0.281 · lift 2.34× |

Measured on **2021–2023 — years the model never saw.**

### What a user does with it

A planner opens the register, filters to their province, and sees the schools to
act on first — each with a score, a national rank, and its three driving
factors. **That is a morning's decision instead of a year's guesswork.**

### Why it can be trusted

The model is a **Logistic Regression Scorecard** — not a black box. Every score decomposes into
visible, auditable weights, so whoever must justify the spend can explain the
decision line by line — to a treasury, a community, or a school that disagrees
with it.

A ranking alone says where to go but not what to bring. Each score breaks into
the factors that produced it — funding tier, staffing levels, enrolment trend,
matric throughput — because a school flagged for a funding reason needs
different help from one flagged for a staffing reason.

## The data was broken, and nothing said so

The brief asks for discrepancy and anomaly detection. We found that the data to
answer the question is already public — and quietly wrong.

**Seven automated detectors over 572,607 records across two datasets return 19
findings, 13 severe enough to change what a model learns.** Not one of them
raises an error:

- **2017 loses 1.44 million learners** nationally and 2018 gains 1.31 million
  back. No country does that.
- **Province codes are unstable** — `KZ`/`KZN`, `GT`/`GP` — turning a country of
  nine provinces into a dataset of eleven.
- **Gauteng's 2023 file** has its key column headed `"G"`, truncated upstream.
  Three thousand schools vanish.
- **724 schools sit at latitude zero** — a point in the Atlantic Ocean.
- **Phase appears in 21 spellings**, quintile in 17, the fee flag in 11.
- **8,792 schools change their recorded phase** between years.

**We audited our own work on the same terms, and it failed too.** Our first PDF
parser trusted each report's header as the layout for the whole file. The
reports do not work that way. It produced 14,005 records claiming more learners
were advanced into matric than sat the exam, and silently destroyed the
pass-rate column — which looked so much like a field the source does not publish
that we removed it from the model and wrote a comment explaining why. The
comment was wrong and the evidence behind it was our own bug.

The fix is verified by arithmetic the source itself provides: where a report
prints both the achieved count and the pass rate, the rate must equal achieved ÷
wrote. **It now holds on 82,979 of 82,979 checkable records.** Pass rate turned
out to be the strongest single variable in the model.

## Quick start

```bash
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Opens at http://localhost:8501. The built tables are committed, so nothing needs
downloading first.

> `streamlit` is not on PATH on every machine. `python -m streamlit` always
> works and is the form used throughout.

### Everything you can run

```bash
python -m streamlit run app/streamlit_app.py   # the app, nine pages
python -m pytest tests/ -v                     # 59 tests

# rebuild from source — only needed to refresh, outputs are committed
python -m src.fetch.emis_masterlists   # 234 provincial spreadsheets
python -m src.fetch.nsc_reports        # 13 matric report PDFs
python -m src.build.nsc_results        # PDFs   -> nsc_results.csv
python -m src.build.school_panel       # sheets -> school_year_panel.csv.gz
python -m src.build.clean              #        -> clean_panel.csv.gz
python -m src.model.features           #        -> model_frame.csv.gz
python -m src.model.train              # the scorecard      -> outputs/
python -m src.model.benchmark          # the forest it is measured against
python -m src.model.charts             # figures            -> outputs/
python -m src.eda.run_audit            # the anomaly findings -> outputs/
```

Every file in `outputs/` is produced by one of these. Nothing in it was copied
from anywhere, and nothing in it is orphaned from code that no longer exists.

Everything runs as a module from the repository root. Running a file by path
(`python src/model/train.py`) breaks the `src.` imports.

## The app, in the order the argument is made

| | Page | |
|---|---|---|
| | **Overview** | the problem, and the four questions |
| 1 | **Data audit** | what is wrong with the data, before anything is claimed from it |
| 2 | **How we built it** | cleaning, target, features, the matric extraction |
| 3 | **The final model** | metrics, confusion matrix, leakage checks, calibration |
| 4 | **Risk list** | the 2025 register, filterable |
| 5 | **School profile** | one school, its score, its three reasons |
| 6 | **Score simulator** | change a factor, watch the score move |
| 7 | **Security** | why it is safe to run |
| 8 | **Business model** | what it costs and who pays |

## Layout

```
app/          the Streamlit application
src/
  common/     paths, identifier normalisation, loading
  fetch/      download from the department's own site
  build/      raw files -> clean tables
  eda/        anomaly detection, weight of evidence
  model/      features, scorecard, scoring, evaluation, charts
datasets/
  raw/        gitignored — rebuilt by src/fetch
  processed/  the built tables, committed
  sources/    reference material on each source
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
  POPIA and are not used. The system holds no personal data by design — not
  because it is well guarded, but because it was never collected.
- **It measures enrolment decline, not dropout.** A learner who transfers to a
  better school and one who leaves education entirely look identical in a
  headcount.
- **It is a triage list, not a verdict.** At 0.694 AUC the ranking is worth
  working from the top of, and not good enough to be believed about any single
  school without a visit.
- **A better-ranking model exists and is not shipped.** A calibrated random
  forest reaches 0.716. It cannot tell a school why it was flagged, so it stays
  a benchmark — and the 0.022 gap is reported rather than hidden, because that
  is the measured price of interpretability.
- **Accuracy is our weakest number and we lead with lift instead.** On a target
  that is 12% positive, predicting that no school ever loses learners scores 88%
  and identifies nobody.
