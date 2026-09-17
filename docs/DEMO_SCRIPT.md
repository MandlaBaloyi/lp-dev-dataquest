# Demo script — The Missing List (about 7 minutes)

A click-by-click talk track. Every number on screen is produced by the
pipeline, so nothing here has to be memorised — the figures below are for
rehearsal, and the app is the source of truth if the two ever disagree.

Nine pages, ordered so the argument builds. Do not jump around.

## Before you present

```bash
python -m streamlit run app/streamlit_app.py
```

Opens at http://localhost:8501. **The built tables are committed, so nothing
needs rebuilding before a demo.** Only run the pipeline if you want to refresh
it from source:

```bash
python -m src.build.clean        # raw panel   -> clean panel
python -m src.model.features     # clean panel -> model frame
python -m src.model.train        # the scorecard
python -m src.model.charts       # figures
```

- Click through all nine pages once before presenting. The first load of each
  caches its data, so the live run is instant.
- Full-width browser window, zoomed to 90%.
- **Backup:** `docs/screenshots/` has captures of five pages — overview, risk
  list, school profile, simulator and how-we-built-it. They predate the
  restructure and **do not cover data audit, the final model, security or
  business model.** Recapture all nine before presenting if the demo is going
  to depend on them.

---

## 1. Overview — the problem (1 min)

> "More than 40% of South African learners who start Grade 1 never finish
> matric. That figure is published every year and nobody disputes it. What is
> **not** published is which schools. You cannot send a district official to a
> percentage."

- Point at the **four questions** table: which provinces, which districts,
  which schools — answered. Which grades — not yet, and say so.
- Headline numbers: **7,681 schools scored** for 2025, **842 on the priority
  tier**, holding **212,893 learners**.
- Be upfront about coverage before anyone asks:
  > "Eight provinces, not nine. The Northern Cape published a Word template
  > where its 2025 masterlist should be. Our audit caught it. The model covers
  > all nine; the register covers the eight that published."

## 2. Data audit — the challenge question (1.5 min)

This is the page that answers the brief directly. Do not rush it.

> "Before we trained anything, we ran seven automated detectors over 572,607
> records. They return 19 findings, 13 severe enough to change what a model
> learns. **Not one of them raises an error.** The files open, the totals look
> plausible."

- Show the **2017 chart**: 1.44 million learners disappear nationally and 1.31
  million come back the next year. No country does that.
- Two or three from the findings table — province codes `KZ`/`KZN` turning nine
  provinces into eleven, Gauteng's 2023 column headed `"G"`, 724 schools at
  latitude zero in the Atlantic Ocean.
- Open the **sources** block and name where the data comes from. This is the
  "references" the judging criteria ask for.
- **Then the honest part, which is the strongest thing on the page:**
  > "We audited our own work on the same terms and it failed too. Our first PDF
  > parser produced 14,005 records claiming more learners were advanced into
  > matric than sat the exam, and it silently destroyed the pass-rate column.
  > We removed pass rate from the model and wrote a comment explaining why. The
  > comment was wrong — the evidence behind it was our own bug. We fixed it,
  > and pass rate turned out to be the strongest variable in the model."

## 3. How we built it (1 min)

- Target, stated as a proxy and not oversold:
  > "The government file has total learners, not grades. So we flag a school
  > losing learners **15 points faster than its province** over two years.
  > That is learner loss, not dropout — a transfer looks identical."
- Cleaning decisions, each with its row cost.
- The split: trained on 61,485 school-years, tuned on 15,357, tested on 23,043.

## 4. The final model (1.5 min)

> "A logistic regression scorecard over 15 variables. Test AUC **0.694** on
> 2021–2023, years it never saw."

- **Confusion matrix** — name the costly error:
  > "A missed school gets nothing. A false alarm gets a visit to a school that
  > turned out fine. Those costs are not symmetric, so we set the threshold for
  > recall, not for accuracy."
- **Accuracy warning** — say it before a judge finds it:
  > "Accuracy is our weakest number and we lead with lift instead. Predicting
  > that no school ever loses learners scores 88% and identifies nobody."
- **Decile chart:** worst tenth loses at **28.5%**, best tenth at **2.43%**.
- **The benchmark**, which is the answer to "why not use a better model":
  > "A calibrated random forest reaches 0.716. It is not what ships, because it
  > cannot tell a school why it was flagged. That 0.022 gap is the measured
  > price of interpretability, and we publish it rather than hide it."
- **Leakage checks** — measured, not asserted:
  > "A random split lifts the tree from 0.692 to 0.731. It has learned to
  > recognise schools, not predict them. That is why we split by year."

## 5. Risk list — where to act (1 min)

- Filter **Province → Limpopo**, **District → Vhembe East**.
  > "This is the list a district director takes into the field: ranked worst
  > first, with the reasons already written."
- Show **Download** — it leaves the app as a spreadsheet.
- **Select rank 1, NTEVHEDZENI**, and open its profile.

## 6. School profile — why this school (1 min)

> "Ntevhedzeni, Vhembe East. 111 learners, rank 1 of 7,681, a 48% chance of
> losing learners faster than its province by 2027 against a 13% base rate."

- Read the three reasons off the screen:
  > "Matric pass rate below 42.8% costs it 37 points. Enrolment volatility
  > costs 17. Small size costs 13. **That is the whole score** — no black box,
  > and a school flagged for a pass-rate reason needs different help from one
  > flagged for a staffing reason."

## 7. Security and business model (30 s)

Only if time allows — otherwise leave them for questions.

- Security: no personal data by design, input validation on every download, the
  model ships as JSON with no executable artefact, and a threat model that
  names the gap we have not closed.
- Business: R612,000 a year against 842 priority schools holding 212,893
  learners. Less than the state has already spent on three Grade 10 learners.

## Close (15 s)

> "Open government data, a list a province can act on this week, and a reason
> next to every school. Thank you."

---

## Likely questions

| Question | Answer |
|---|---|
| Why not just use matric pass rates? | We do — it is the strongest variable in the model. But it only measures learners who reached the exam. The register is about the ones who never got there. |
| Is this dropout? | No. It is learner loss, and it includes transfers. It is the best open signal until grade-level counts are published. |
| Why is AUC 0.694 and not higher? | The masterlist carries little beyond enrolment history. Adding matric results took it from 0.654 to 0.694. The remaining gain needs grade-level counts, which are held under separate permission. |
| Why a scorecard and not the forest? | The forest scores 0.716 and cannot explain a single flag. This output directs public money, so it has to be explainable to the school it is about. We publish the gap. |
| Why are small schools ranked high? | Partly real, partly arithmetic — losing 20 learners is a bigger share of 150. Size is in the model as a factor, and it is visible in the score breakdown. |
| Where is the Northern Cape? | It published a Word template instead of its 2025 masterlist. Our audit found it. |
| Could you game it? | Every factor comes from published enrolment and exam figures, so gaming the score means misreporting enrolment to the department — a different and larger problem. |
| Is any of this personal data? | None. The smallest unit is a school. Learner records are protected under POPIA and we have no lawful basis to process them, so we never collected any. |
| How do we know your numbers are right? | Rebuild them. Every table is produced by a committed script from public sources, and where the source prints both an achieved count and a pass rate, the arithmetic is checked — it holds on 82,979 of 82,979 checkable records. |
