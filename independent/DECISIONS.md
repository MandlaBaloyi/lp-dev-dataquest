# Cleaning and modelling decisions: independent track

Every choice made between the raw panel and the trained model, with the reason
and the number of rows it touched. The counts come from
`outputs/cleaning_log.json`, which `python -m independent.src.clean` writes.
Rule IDs (D1, D2, …) match the comments in `src/clean.py`.

Input: `datasets/processed/school_year_panel.csv.gz`, which has 478,761 rows,
29,655 EMIS numbers, 2007–2025 and 20 columns. Nothing else from the repository
was used. The primary track's cleaning code, decisions and model table were
deliberately not read.

Output: `data/clean_panel.csv.gz`, which has 146,944 rows and 9,157 schools
(secondary and combined only), and `data/model_frame.csv.gz`, which holds the
features and target.

---

## What was wrong with the data

We profiled each column (distinct values, missingness, per-year and
per-province breakdowns) before planning. These are the problems we found, in
order of how much damage they would do if left in place.

| # | Problem | Evidence | Why it matters |
|---|---|---|---|
| 1 | **The 2017 snapshot is corrupt** | National enrolment is 12.93M in 2016, 11.50M in 2017 and 12.81M in 2018. In a normal year 3.7% of schools move >30%; in 2017 it is 11.9%, with 23% in EC and 18% in LP | Any "enrolment fell" target fires for thousands of schools that lost nobody |
| 2 | **One file supplies eight years** | `*_2013Q4.xlsx` provides every row for 2007–2014 | Those years are one publication's history, not eight independent snapshots. Training years are noisier than recent ones (see the IV note in REPORT.md) |
| 3 | **Phase is reclassified over time** | 1,573 schools labelled COMBINED in 2016 are PRIMARY by 2023. COMBINED row counts fall from 4,600 to 2,400 | "Combined" does not reliably mean the school has Grades 10–12 |
| 4 | **Coordinates are broken four ways** | 24,261 rows have lat/lon swapped; comma decimals (`-23,906943`); lost decimal points (values of ±3×10¹⁴); 724 zeros | Distances between schools are meaningless until fixed |
| 5 | **Educators missing for all of 2014** | 25,330 of 25,330 rows | Learner-educator ratio and educator change are undefined for a whole training year |
| 6 | **Categorical spellings vary** | Quintile `3`/`Q3`/`NQ3`/`TO BE UPDATED`; sector `PUBLIC`/`Public`/`Independent/Private`; no-fee `YES`/`No Fee`/`Y`; phase in 21 spellings | Each spelling becomes its own category |
| 7 | **Column shift in WC 2021** | 1,740 rows have sector = `ORDINARY` (the type value) | Sector is wrong for a province-year |
| 8 | **MP publishes no districts for 2007–2013** | 18,421 rows `NOT APPLICABLE` | District-level features would be missing for a province and a period together |
| 9 | **Isolated one-year spikes** | For example, a school with 8,360 learners in 2011 only | A single bad year creates a false loss two years later |
| 10 | **Placeholder values** | 126 schools listed as open with 0 learners, and 25 `-` values | Look like real zeros |

We checked a few more things that turned out not to be problems. There are no
duplicate (emis, year) pairs. Learners are almost never missing (30 rows).
About 2% of schools report exactly the same count as the year before, which is
plausible for small stable schools, so we left them alone.

---

## Cleaning rules

| ID | Rule | Rows / schools touched | Reason |
|---|---|---|---|
| D1 | Drop the 2017 snapshot entirely | 24,486 rows | Problem 1. Fixing it school by school is guesswork, and dropping it costs one training year. Changes are annualised across the gap instead (F1) |
| D2 | `-`, blank and 0 learners → missing; 0 educators → missing | 30 + 126 learners; 67 educators | An open school with zero learners is a reporting gap |
| D2 | Educators → missing where learners/educators > 150 | 271 rows | A count in the wrong column; no functioning school runs at 150:1 |
| D2 | 2014 educators left missing (not imputed) | 25,330 rows | Imputing a whole year would invent a trend. The WoE "missing" bin absorbs it |
| D3 | Learners → missing when >2.5× or <0.4× both neighbours, and the neighbours agree within 25% | 203 rows | Problem 9. The rule looks one year ahead, which is acceptable for cleaning history but not possible for the latest year (see Limitations) |
| D4 | Parse comma decimals; swap lat/lon where lat > 0 and lon < 0; rescale out-of-range values by powers of ten into SA's bounding box; zeros → missing; then use one location per school (median across years) | 24,261 swapped; 3,672 rescaled or dropped; 1,274 schools (all phases) left without a location | Problem 4. Schools don't move, so the median across years also absorbs one-off typos |
| D5 | Upper-case and trim all categoricals. Sector: `INDEPENDENT/PRIVATE` → INDEPENDENT; anything other than PUBLIC/INDEPENDENT → missing; then the school's modal sector for every year | 1,740 shifted values | Problems 6 and 7. Sector does not change year to year |
| D5 | Status: flag `PENDING CLOSE`, `IN PROCESS OF CLOSING`, `NOT FUNCTIONAL`, etc. as `closing_flag` | 136 rows | Kept in the data. Not used in the model: 15 in-scope rows, none with a label |
| D6 | Quintile: strip `Q`/`NQ`, keep 1–5, anything else → missing; then carry forward within a school (never backward) | 38,620 missing before, 37,223 after (all phases) | Backward filling would give a year a value published later |
| D6 | No-fee: YES/Y/NO FEE → 1; NO/N/FEE CHARGING/FEE PAYING → 0; `FREE CHARGING` (3 rows) → missing; carry forward | 98,856 still missing (all phases) | `FREE CHARGING` could be a typo of either value, so we didn't guess |
| D6 | Urban/rural: DEEP RURAL → RURAL, PERI-URBAN → URBAN, `TO BE UPDATED`/`NO RESPONSE` → missing; carry forward | 75,908 still missing (all phases) | 8 peri-urban rows are too few for their own category |
| D7 | District: `NOT APPLICABLE`/`UNKNOWN` → missing; each school gets its most recent real district name for all years; key = province + district | 18,421 N/A rows; 1,093 rows still without a district | Problem 8, and renamed districts (e.g. municipal renames) would otherwise split one district into two |
| D8 | Drop `circuit`; don't use `old_emis`/`new_emis` | n/a | Circuit has 1,781 spellings and 17% blanks. Renumbering is handled by leaving vanished schools unlabelled (T3) |
| D9 | **Population**: ordinary schools (not special needs) labelled SECONDARY in most of their years, or COMBINED in most years and **never** PRIMARY | 6,622 secondary + 2,535 combined kept; 1,836 mostly-combined schools excluded for having been PRIMARY at some point | Problem 3. A school the department has ever called primary most likely has no Grade 10–12 learners |

---

## Target

| ID | Decision | Reason |
|---|---|---|
| T1 | **loss = 1** when a school's enrolment change from year *t* to *t+2* is at least **15 percentage points worse** than the median change of in-scope schools in its province over the same window | See below |
| T2 | Only schools with ≥100 learners at *t* are labelled | On a 40-learner school, 6 learners is 15%. Small denominators turn noise into events |
| T3 | Schools with no row at *t+2* are **unlabelled**, not counted as losses | 1,604 school-years. A missing row is as likely to be an EMIS renumbering or a merger as a closure, and a closure moves learners rather than losing them |
| T4 | Horizon = 2 years | One year is dominated by reporting noise; three years costs another year of labels and moves the warning further from action |

**Why this target.** The panel has only total learners per school, with no
grade breakdown, so true cohort dropout (Grade 10 → Grade 12 of the same
learners) cannot be computed from it. The closest honest proxy is "this school
is losing learners faster than schools around it." Adjusting for the province
does two things:

1. It removes shocks that hit a whole province, which in this data are mostly
   publication artefacts (the 2009 dip, the 2018 rebound) and not something a school-level
   intervention can address.
2. It stops the list from simply reproducing provincial migration (the Eastern
   Cape shrinking while Gauteng grows).

The 15-point threshold makes the positive class 13.7% of school-years, and the
median positive school loses 23% of its learners (98 learners) over the two
years.

We considered and rejected three alternatives:
- A raw ≥15% drop, which the Eastern Cape dominates for demographic reasons.
- A persistent decline over three consecutive years, which leaves too few
  positives and too late a warning.
- Matric pass rate, which the brief rules out as a different question.

---

## Features

All features for year *t* use only rows from years ≤ *t*. A test pins this
(`test_features_do_not_see_the_future`).

| ID | Decision | Reason |
|---|---|---|
| F1 | Changes are annualised over the actual gap: last year's change looks back 1 year, or 2 if the prior year is missing (e.g. 2018 vs 2016); the 3-year trend looks back 3 years, or 4 | Keeps the features defined across the dropped 2017 without inventing it |
| F2 | Volatility = standard deviation of yearly log changes over the last 5 observations (min 3) | Separates noisy reporters from steady declines |
| F3 | Peak ratio = learners ÷ the school's own maximum so far | Captures sustained decline from a peak |
| F4 | Context: province-relative change, district median change, district FET school count, number of FET schools within 5 km and 10 km, neighbours' median change, size relative to neighbours | Tests the idea that learners leave for nearby schools |
| F5 | `years_observed` built and then **excluded** | The panel starts in 2007, so the feature mostly encodes the calendar year and drifts between train (max 10) and test (up to 17) |

---

## Splitting, binning and selection

| ID | Decision | Reason |
|---|---|---|
| S1 | **Train** on 2008–2016, **validate** on 2018–2019, **test** on 2021–2023, **score** 2025 | By year, never at random. Every training outcome (≤2018) is known before the first validation year; every validation outcome (≤2021) is known by the first test year. 2015 has no label (its *t+2* is the dropped 2017); 2020 is skipped so validation outcomes never postdate test features; 2007 has no lag features |
| S2 | WoE bins fitted **on training rows only** and never refitted | Brief, mistake 2. A test pins this |
| S3 | Numeric bins: up to 8 quantile bins; merge any bin under 5% of rows; merge neighbours whose WoE differs by < 0.05; **not** forced monotonic | Last year's change has a real U-shape (see REPORT.md); forcing monotonic bins would erase it |
| S4 | Missing values get their own bin; a missing bin with <1% of training rows gets WoE 0 | 76 training rows had no location, which gave an extreme WoE from almost no evidence and pushed schools with a data gap to the top of the list |
| S5 | Categories under 2% → OTHER; categories never seen in training → WoE 0 | Stability |
| S6 | Selection: IV ≥ 0.02, then drop the lower-IV member of any pair with \|r\| > 0.7, then drop variables whose coefficient takes the wrong sign | A wrong-signed variable is only correcting another one, and no official can read that |
| S7 | Decision threshold chosen on **validation** as the highest probability that still catches 70% of loss schools, then applied unchanged to test | A missed school costs more than a wasted visit, so we optimised for recall (see REPORT.md) |
| S8 | Scorecard scaling: 600 points at 50:1 odds of *no loss*, 20 points to double the odds. **Lower score = higher risk** | Standard scorecard convention |
| S9 | 2025 ranking uses the model exactly as evaluated (trained on 2008–2016), not a refit | What we tested is what we ship. Refitting on all labelled years is the obvious next step once both tracks agree on the target |
