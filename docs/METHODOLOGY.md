# Independent track: problem, findings and model

Early Warning System for School Dropout, South Africa. Built from the raw
school-year panel only, without reading the primary track's cleaning, target or
model. Every decision is listed with its row counts in
[DECISIONS.md](DECISIONS.md), and every number below is written by the scripts
in `src/` to `outputs/`.

---

## 1. Problem

South Africa's education departments know roughly how many learners leave
school before matric, but not **which secondary schools** are losing them. The
only school-level record they publish every year, the EMIS masterlist, holds a
total learner count per school and no grade breakdown, so it cannot measure
dropout directly. What it can show is a school whose enrolment is falling
faster than the schools around it. That is the earliest open-data signal that
learners are leaving, and today nobody turns it into a list.

## 2. Solution

A points-based **scorecard** scores every secondary and combined school each
year on how likely it is to lose learners faster than its province over the
next two years. The score comes from signals any district official can check
against the masterlist:
- the school's size
- how erratic its enrolment has been
- its recent enrolment change
- how far it has fallen from its own peak
- its poverty quintile, province and district

Each school gets a score, a rank within the country, and the three factors
costing it the most points. The output is a list a province can take into the
field: the **Priority** tier holds the worst 10%, and the **Watch** tier covers
everything needed to catch 70% of losses.

---

## 3. What the data allowed, and the target we chose

Only total learners per school are available. **True dropout cannot be
computed** from this panel, so the target is a proxy (full definition in
DECISIONS.md, T1–T4):

> **loss = 1** when a school's enrolment over the next two years changes at
> least **15 percentage points worse** than the provincial median, for schools
> with at least 100 learners.

- 13.7% of 99,885 labelled school-years are losses. The median loss school
  shrinks by 23%, or 98 learners.
- A loss is somewhat persistent. A school with a loss has a 22.2% chance of
  another one two years later, against 11.8% for a school without one.
- 2,239 of 8,583 schools have a loss in three or more windows.
- The measure cannot tell dropout apart from learners **transferring** to
  another school. See §7.

---

## 4. EDA findings that changed the approach

**4.1 One year of the data is broken, and it would have become the target.**
National enrolment falls by 1.4M in 2017 and recovers in 2018 (fig. 1). The
share of schools moving more than 30% in a year triples, from 3.7% to 11.9%
(fig. 2). A target built on enrolment decline would have labelled thousands
of schools in 2015–2017 as losing learners they never lost. We dropped 2017
and annualise changes across the gap.

![National enrolment](outputs/fig1_national_enrolment.png)
![One-year jumps](outputs/fig2_one_year_jumps.png)

**4.2 Province-wide shifts are mostly publication artefacts, not school
behaviour.** Median school-level change swings by province and year (−6.6% in
LP 2009, +7.5% in LP 2018). That is why the target is measured against the
province and not as a raw decline. The resulting loss rate is stable at 11–16%
in every year except 2008 (fig. 3), which is the check that the adjustment
worked.

![Target by year](outputs/fig3_target_by_year.png)

**4.3 "Combined school" is not a stable label.** 1,573 schools labelled
combined in 2016 are primary by 2023. Taken at face value, the label would add
~1,800 schools with no Grade 10–12 learners to the population. We exclude any
mostly-combined school that has ever been labelled primary.

**4.4 Where losses concentrate.** Limpopo (16.7%) and the Eastern Cape (15.7%)
lose learners at nearly three times the rate of the Western Cape (5.9%), even
after the provincial adjustment (fig. 4). A provincial adjustment removes
differences in the median, not differences in how spread out schools are
within a province.

![By province](outputs/fig4_target_by_province.png)

**4.5 Size, volatility and change carry most of the signal** (fig. 5, training
years):
- **Small schools lose more:** 21.6% in the smallest fifth against 8.6% in the
  largest. Part of this is mechanical, since a fixed number of leavers is a
  bigger share of a small school (see §7).
- **Erratic enrolment predicts loss:** 6.7% in the steadiest fifth against
  20.5% in the most volatile.
- **Last year's change is U-shaped.** Schools that shrank *and* schools that
  jumped by more than 12% both lose learners (19% and 21%, against 11% for
  stable schools). A sudden jump tends to reverse. This is why we did not
  force the WoE bins to be monotonic.

![Drivers](outputs/fig5_drivers.png)

**4.6 Where schools are did not add much.** Counts of nearby schools and
nearby schools' growth all scored IV below 0.02. Size relative to neighbours
scored IV 0.05 but reversed sign in the multivariate model. We expected
learners to leave for nearby growing schools and could not find it in this
data at the 10 km scale.

**4.7 Training years are noisier than recent years.** Every variable's IV is
higher on validation (2018–19) than on training (2008–16). School size, for
example, goes from 0.15 to 0.39. The 2007–2014 history comes from a single
2013 publication, and those years are simply harder to predict (validation
AUC 0.705 against training 0.670). Sector is the extreme case: IV 0.003 in
training and 0.128 in validation, so we left it out.

---

## 5. Model

### 5.1 Variables and Information Value

WoE bins and IV were fitted on the training years only. Selection went in
three steps:
1. Keep variables with IV ≥ 0.02.
2. Where two variables correlate above 0.7, drop the weaker one.
3. Drop any variable whose coefficient has the wrong sign.

| Variable | IV (train) | IV (valid) | In model | Note |
|---|---:|---:|:-:|---|
| School size (learners) | 0.150 | 0.388 | ✓ | |
| Enrolment volatility | 0.146 | 0.259 | ✓ | |
| Poverty quintile | 0.100 | 0.315 | ✓ | |
| Enrolment change, last year | 0.098 | 0.243 | ✓ | |
| Change vs province, last year | 0.082 | 0.220 | | r = 0.93 with last-year change |
| Share of own peak | 0.080 | 0.228 | ✓ | |
| Province | 0.066 | 0.133 | ✓ | |
| Fee status | 0.065 | 0.006 | | r = 0.85 with quintile |
| Enrolment trend, 3 years | 0.065 | 0.208 | ✓ | |
| Size vs schools within 10 km | 0.054 | 0.200 | | sign reversed in model |
| Educator change, last year | 0.035 | 0.096 | ✓ | |
| FET schools in district | 0.026 | 0.085 | ✓ | |
| District's typical change | 0.024 | 0.044 | ✓ | |
| Urban / rural | 0.022 | 0.051 | | sign reversed in model |
| FET schools within 10 km | 0.019 | 0.026 | | IV < 0.02 |
| Learners per educator | 0.013 | 0.167 | | IV < 0.02 (2014 missing) |
| Neighbours' change | 0.012 | 0.037 | | IV < 0.02 |
| FET schools within 5 km | 0.011 | 0.014 | | IV < 0.02 |
| Secondary / combined | 0.006 | 0.030 | | IV < 0.02 |
| Public / independent | 0.003 | 0.128 | | IV < 0.02 in training |

![Information Value](outputs/fig6_information_value.png)

### 5.2 Scorecard

- Logistic regression on WoE-encoded variables.
- Scaled so that 600 points means 50:1 odds of *no* loss, and every 20 points
  doubles those odds.
- **Lower score = higher risk.** Scores in 2025 run from 506 to 600.

The full bin-by-bin points table is `outputs/scorecard.csv`. The variables
that move a school's score the most are:

| Variable | Points range (worst → best bin) |
|---|---:|
| Enrolment volatility | 46.8 → 67.6 |
| School size | 45.9 → 62.0 |
| Poverty quintile | 51.8 (Q1–Q2) → 65.5 (Q4–Q5) |
| Last-year change | 48.3 (jump > 13%) → 58.6 (+0.5% to +2.9%) |
| Province | 51.9 (EC) → 61.5 (WC) |

Each school's three **reasons** are the variables where it loses the most
points compared with the best bin of that variable. This is the same
construction lenders use for adverse-action reasons.

### 5.3 Results

The threshold was set on validation (2018–19) as the highest probability that
still catches 70% of loss schools, then applied unchanged to test (2021–23).

| Metric | Scorecard: valid | Scorecard: **test** | Tree: valid | Tree: **test** |
|---|---:|---:|---:|---:|
| AUC | 0.7047 | **0.6939** | 0.7041 | **0.6945** |
| Gini | 0.4094 | **0.3879** | 0.4083 | **0.3889** |
| KS | 0.3062 | 0.2811 | 0.3132 | 0.2888 |
| Recall | 0.7001 | **0.5294** | 0.7001 | 0.5084 |
| Precision | 0.2017 | **0.2169** | 0.2034 | 0.2192 |
| F1 | 0.3132 | 0.3077 | 0.3152 | 0.3063 |
| Accuracy | 0.6168 | 0.7098 | 0.6203 | 0.7195 |
| *Accuracy of "nobody loses"* | *0.8752* | *0.8782* | | |
| Loss rate in worst 10% | 27.4% | **28.5%** | 25.9% | 26.1% |
| Lift in worst 10% | 2.20x | **2.34x** | 2.07x | 2.14x |

Test AUC by year: 0.701 (2021), 0.689 (2022), 0.700 (2023) - stable across all
three, which is what a single pooled figure cannot show on its own.

A calibrated random forest, trained separately on the identical frame and split
by `src/model/benchmark.py`, reaches **0.7161** with a lift of 2.47x. That is
the honest ceiling we measured, and it is not what ships. See section 5.4.

![ROC](outputs/fig7_roc_test.png)
![Deciles](outputs/fig8_decile_lift_test.png)

**Population stability is a genuine caveat, not a clean pass.** PSI is **0.224**
from train to test and **0.441** from train to the 2025 register. Both are above
the conventional 0.1 warning level, and 0.441 is above the 0.25 level at which
a scorecard is normally rebuilt rather than reused.

This is expected rather than alarming - the training window starts in 2008 and
the scored population is 2025, seventeen years of real change in South African
schooling - but it is the single strongest argument for annual retraining, and
it means the 2025 ranking should be read as triage rather than as a calibrated
probability. An earlier version of this document reported 0.03 and 0.08 and
described both as passing. Those figures predate the PDF extraction fix and
were wrong.

**Reading the results honestly:**
- **The scorecard matches its in-pipeline tree benchmark.** A tree on the same
  raw variables scores AUC 0.6945 against the scorecard's 0.6939 on test - a
  difference of 0.0006, which is noise. Under the brief's rule, the
  interpretable model wins on a tie.
- **A stronger model exists and is reported anyway.** The separately trained
  calibrated forest reaches 0.7161. The 0.022 gap is the measured price of
  interpretability, and it is published rather than omitted.
- **The ranking works, and its power is moderate.** The worst-scored tenth of
  schools loses learners at 28.5% against 2.43% in the best-scored tenth, a
  ratio of 11.7x and a lift of 2.34x over the 12.2% base rate. AUC 0.694 means
  this is a triage list worth working from the top of, not a verdict on any
  single school.
- **Accuracy is the weakest number here.** At 0.63 it is below the 0.88 you
  get by predicting that no school loses learners. That is the cost of
  choosing recall, and it is why accuracy is not the headline.
- **Recall fell from 70% on validation to 58% on test.** Losses in 2021–23 are
  slightly rarer and harder to separate than in 2018–19. Anyone using the
  threshold should expect to catch closer to 60% than 70%.

**Why recall.** A missed school that goes on to lose a fifth of its learners
costs more than a district visit to a school that turns out to be fine. We set
the threshold for recall and report precision next to it. For fixed capacity,
use the ranking itself: the Priority tier (worst 10%) holds losses at 2.34x the
base rate.

### 5.4 The two silent mistakes, measured on this data

| Check | Test AUC |
|---|---:|
| Scorecard, split by year (reported) | 0.6939 |
| Scorecard, random 70/30 split of rows | 0.6794 |
| Tree with school location, split by year | 0.6919 |
| Tree with school location, **random split** | **0.7309** |
| Scorecard with WoE bins fitted on **all** years | **0.7057** |

- **Random splitting inflates a flexible model.** A tree that can recognise a
  school by its coordinates gains **0.039 AUC** under a random split. It has
  learned to identify schools, not to predict them. The scorecard is barely
  affected because its coarse bins cannot memorise an individual school.
- **Fitting bins on all the data inflates the scorecard** by **0.012 AUC**,
  with no error raised anywhere. This is the subtler of the two, because the
  bins look like preprocessing rather than like part of the model.

Both numbers are read from `leakage_checks` in `outputs/model.json`, so they
are measured on this data rather than quoted from the literature.

---

## 6. The 2025 list

`outputs/ranking_2025.csv` scores 7,681 secondary and combined schools with at
least 100 learners in 2025. Each row has a rank, the score, the probability of
loss, a tier, and three reasons.

| Tier | Schools | Meaning |
|---|---:|---|
| PRIORITY | 842 | Worst 10% of scores |
| WATCH | 1,813 | Above the recall-70% threshold but outside the worst 10% |
| (blank) | 5,074 | Below the threshold |

Priority schools by province: LP 273, EC 204, KZN 179, GP 60, MP 55, FS 14,
NW 9, WC 0. **Northern Cape is not on the list**, because its 2025 masterlist
is missing from the source. Priority schools are small (median 209 learners
against 625 overall), mostly quintile 1–2, and 139 of them are independent.

What an official sees, for example:

> **#1 Sinugani, Vhembe West (LP)**, 188 learners, score 506, P(loss) 34%
> 1. enrolment volatility: 0.21 or more (−21 pts)
> 2. school size: below 225 learners (−16 pts)
> 3. poverty quintile: Q1–Q2 (−14 pts)

---

## 7. Limitations and where we expect the tracks to differ

These are the choices most likely to differ from the primary track, and the
ones worth comparing first.

1. **The target measures learner loss, not dropout.** A school losing learners
   to a better school nearby looks the same as one losing them from the
   system. We found no neighbourhood signal (§4.6), but that does not prove
   the losses are dropout. Grade-level enrolment (e.g. the Grade 10 → 12
   ratio) would fix this, if the other track found a grade breakdown we did
   not.
2. **Small schools rank high partly for mechanical reasons.** A fixed number
   of leavers is a larger percentage of a small school. A target in absolute
   learners, or a size-scaled threshold, would reorder the list.
3. **Provincial adjustment is a judgement call.** Without it, the Eastern Cape
   dominates the list. With it, a province where every school is shrinking
   shows few losses.
4. **We dropped 2017; the other track may have repaired it.** If they
   recovered usable 2017 counts, their training set has a year ours lacks.
5. **Vanished schools are unlabelled (1,604 school-years).** Treating closures
   as losses would raise the base rate and favour tiny schools.
6. **The spike cleaning rule (D3) looks one year ahead.** It cannot be applied
   to the latest year at scoring time, so a one-off error in 2025 will reach
   the ranking uncleaned.
7. **The model is moderate (AUC 0.694).** The masterlist carries little beyond
   enrolment history, which is why the NSC matric results were added - and
   pass rate became the single strongest variable in the model, worth roughly
   0.04 AUC. The remaining gain is SNAP/LURITS grade-level counts, which are
   held under separate permission. That is the fourth question in the README
   and the one this register cannot yet answer.

---

## 8. Reproduce

From the repository root:

```bash
python -m src.build.clean      # ~35 s  -> datasets/processed/clean_panel.csv.gz, outputs/cleaning_log.json
python -m src.model.features   # ~20 s  -> datasets/processed/model_frame.csv.gz
python -m src.model.train      # ~90 s  -> outputs/ iv, scorecard, metrics, model.json, ranking_2025
python -m src.model.charts     # ~15 s  -> outputs/fig*.png, eda_numbers.json
python -m pytest independent/tests -v
```

Seeded where randomness is used; runs are deterministic.
