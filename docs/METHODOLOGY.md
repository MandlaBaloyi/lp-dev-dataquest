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
AUC 0.69 against training 0.65). Sector is the extreme case: IV 0.003 in
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
| AUC | 0.692 | **0.654** | 0.686 | **0.657** |
| Gini | 0.384 | **0.309** | 0.371 | **0.313** |
| KS | 0.298 | 0.225 | 0.286 | 0.232 |
| Recall | 0.700 | **0.576** | 0.700 | 0.586 |
| Precision | 0.196 | **0.180** | 0.190 | 0.180 |
| F1 | 0.306 | 0.274 | 0.299 | 0.276 |
| Accuracy | 0.604 | 0.628 | 0.590 | 0.625 |
| *Accuracy of "nobody loses"* | *0.875* | *0.878* | | |
| Loss rate in worst 10% | 25.3% | **21.7%** | 25.1% | 20.9% |
| Lift in worst 10% | 2.02× | **1.78×** | 2.01× | 1.72× |

Test AUC by year: 0.666 (2021), 0.642 (2022), 0.662 (2023). The score
distribution is stable: PSI is 0.03 from train to test and 0.08 from train to
2025, both below the 0.1 warning level.

![ROC](outputs/fig7_roc_test.png)
![Deciles](outputs/fig8_decile_lift_test.png)

**Reading the results honestly:**
- **The scorecard matches the benchmark.** A gradient-boosted tree on the same
  raw variables scores AUC 0.657 against the scorecard's 0.654 on test, and it
  overfits badly (training AUC 0.83). Under the brief's rule, the
  interpretable model wins.
- **The ranking works, but its power is modest.** The worst-scored tenth of
  schools loses learners 8× as often as the best-scored tenth (21.7% against
  2.6%). AUC 0.65 means this is a triage list, not a verdict.
- **Accuracy is the weakest number here.** At 0.63 it is below the 0.88 you
  get by predicting that no school loses learners. That is the cost of
  choosing recall, and it is why accuracy is not the headline.
- **Recall fell from 70% on validation to 58% on test.** Losses in 2021–23 are
  slightly rarer and harder to separate than in 2018–19. Anyone using the
  threshold should expect to catch closer to 60% than 70%.

**Why recall.** A missed school that goes on to lose a fifth of its learners
costs more than a district visit to a school that turns out to be fine. We set
the threshold for recall and report precision next to it. For fixed capacity,
use the ranking itself: the Priority tier (worst 10%) holds losses at 1.8× the
base rate.

### 5.4 The two silent mistakes, measured on this data

| Check | Test AUC |
|---|---:|
| Scorecard, split by year (reported) | 0.654 |
| Scorecard, random 70/30 split of rows | 0.656 |
| Tree with school location, split by year | 0.655 |
| Tree with school location, **random split** | **0.707** |
| Scorecard with WoE bins fitted on **all** years | **0.670** |

- **Random splitting inflates a flexible model.** A tree that can recognise a
  school by its coordinates gains 0.05 AUC under a random split, while its
  honest score is unchanged. The scorecard barely moves because its coarse
  bins cannot memorise schools.
- **Fitting bins on all the data inflates the scorecard** by 0.016 AUC, with
  no error raised.

---

## 6. The 2025 list

`outputs/ranking_2025.csv` scores 7,681 secondary and combined schools with at
least 100 learners in 2025. Each row has a rank, the score, the probability of
loss, a tier, and three reasons.

| Tier | Schools | Meaning |
|---|---:|---|
| PRIORITY | 794 | Worst 10% of scores |
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
7. **The model is modest (AUC ≈ 0.65).** The masterlist carries little beyond
   enrolment history. The biggest likely gains are from open sources this
   track did not add: NSC Grade 12 entries per school (cohort size at the
   end), and SNAP/LURITS grade counts if published openly.

---

## 8. Reproduce

From the repository root:

```bash
python -m src.clean      # ~35 s  -> data/clean_panel.csv.gz, outputs/cleaning_log.json
python -m src.features   # ~20 s  -> data/model_frame.csv.gz
python -m src.train      # ~90 s  -> outputs/ iv, scorecard, metrics, model.json, ranking_2025
python -m src.charts     # ~15 s  -> outputs/fig*.png, eda_numbers.json
python -m pytest independent/tests -v
```

Seeded where randomness is used; runs are deterministic.
