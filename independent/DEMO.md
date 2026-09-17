# Demo script: learner-loss early warning (about 7 minutes)

A click-by-click talk track for presenting the independent track live.
Every number on screen comes from the pipeline outputs, so nothing here needs
to be memorised. The numbers below are there for rehearsal.

## Before you present

```bash
# once, from the repository root (about 3 minutes)
python -m independent.src.clean
python -m independent.src.features
python -m independent.src.train
python -m independent.src.charts

# start the app
python -m streamlit run independent/app/streamlit_app.py
```

- Open http://localhost:8501 and click through all five pages once. The first
  load of each page caches its data, so the live run is instant.
- Keep a browser window at full width, zoomed to 90%.
- **Backup:** if the laptop or network fails, `docs/screenshots/` has a
  full-page capture of every page.

---

## 1. Overview: the problem (1 min)

> "South Africa loses about 40 of every 100 learners before matric. That number
> is published every year. What isn't published is **which schools**. You
> can't send a district official to a percentage."

- Point at the **four cards**: 7,681 schools scored for 2025, and 794 on the
  priority list.
- Point at **"Does the ranking hold up on unseen years?"**:
  > "We trained on 2008–2016 and tested on 2021–2023, years the model never
  > saw. The schools we rank worst lost learners at **22%**; the ones we rank
  > best at **2.6%**. That's an 8× difference."
- Point at **"How it works"**, card 2. Say plainly that this is a proxy:
  > "The government file has total learners, not grades. So we flag a school
  > that loses learners **15 points faster than its province** over two years."

## 2. Risk list: where to act (1.5 min)

- Click **Risk list**. The map lights up Limpopo, the Eastern Cape and
  KwaZulu-Natal.
- Filter **Province → Limpopo**, then **District → Vhembe West**.
  > "This is the list a district director would take into the field: ranked
  > worst first, with the reasons already written."
- Point at the **Top reason** column; the reasons are plain language.
- Show the **Download** button: "It leaves the app as a spreadsheet."
- **Select the first row** (Sinugani), then **Open profile**.

## 3. School profile: why this school (1.5 min)

> "Sinugani: 188 learners, rank 1 of 7,681, a 34% chance of losing learners
> faster than its province by 2027, against a national average of 13%."

- **Why this score**: read the three reasons.
  1. Enrolment swings by more than a fifth a year.
  2. It's small: under 225 learners.
  3. It's quintile 2, one of the poorest.
- **Enrolment history**: "Down from about 450 to 188. The model saw only the
  history up to 2025."
- **Highest-risk schools in the same district**: "Three more schools in the
  same district are in the top 10. That's a cluster worth one visit."
- Click **Open the simulator**.

## 4. Score simulator: it's not a black box (1.5 min)

> "Every point in this score can be traced. Watch."

- Drag **Enrolment volatility** down to about **0.03**. The score jumps by
  roughly 20 points, and the **Points by factor** table shows exactly where.
- Set **Learners** to **1,200**. The score rises again.
- Set **Poverty quintile** to **Q5**. The school drops out of the priority
  tier to **Lower risk**, and its rank moves from 1 to the thousands.
  > "No factor is hidden. An official can check every one of these against
  > the department's own masterlist."
- Optionally open **The full scorecard** expander to show all the bands and
  their points on one screen.

## 5. How we built it: why the numbers can be trusted (1.5 min)

- **Data quality** tab:
  > "The government file has a hole in it. In 2017 national enrolment drops by
  > 1.4 million and comes back the next year. A naive model would have flagged
  > thousands of schools that lost nobody. We found ten defects like this and
  > fixed every one; the table shows how many rows each touched."
- **Performance** tab:
  > "Our readable scorecard scores AUC 0.654. A black-box gradient-boosted
  > model scores 0.657, which is level. So we chose the one an official can
  > read."
  - Mention that accuracy isn't the headline number: predicting that nobody
    leaves would score 88%.
- **Leakage checks** tab:
  > "Two mistakes inflate a model silently. We measured both: a random split
  > lifts the black-box model from 0.655 to 0.707, and fitting bins on all
  > the data lifts ours to 0.670. The numbers we report avoid both."
- **Limitations** tab, one line:
  > "This measures learners lost, not dropout. Transfers look the same. That's
  > the first thing we'd fix with grade-level data."

## Close (15 s)

> "Open data, a list a province can act on this week, and a reason next to
> every school. Thank you."

---

## Likely questions

| Question | Answer |
|---|---|
| Why not just use matric pass rates? | They measure learners who wrote the exam. This is about the ones who never got there. |
| Is this dropout? | No, it's learner loss, and it includes transfers. It's the best open signal until grade-level counts are published. See Limitations. |
| Why is AUC only 0.65? | The masterlist carries little beyond enrolment history. It is still an 8× separation between the top and bottom tenths, which is enough to decide where to look first. |
| Why a scorecard and not the tree? | Same accuracy (0.654 vs 0.657), and the scorecard explains every point. |
| Why are small schools ranked high? | Partly real, partly arithmetic: losing 20 learners is a bigger share of 150. It's the first thing we'd compare with the other track. |
| Where is the Northern Cape? | Its 2025 masterlist was not published. |
| Could you game it? | Every factor comes from published enrolment figures, so gaming the score means misreporting enrolment, which is a separate problem. |
