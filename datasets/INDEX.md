# Early Warning System for School Dropout — Data Inventory

**Goal:** predict school-level dropout for Grade 10–12 cohorts, Western Cape pilot.

**Last verified:** 2026-09-16. Every claim below was checked by downloading the file and
inspecting its columns — not inferred from a portal description.

---

## The complete requirement list

| # | What the model needs | Used for | Status | Source |
|---|---|---|---|---|
| 1 | EMIS number (join key) | joining everything | **have** | EMIS masterlists |
| 2 | Quintile / no-fee flag | feature | **have** | EMIS masterlists |
| 3 | District, circuit, urban/rural, GPS | feature | **have** | EMIS masterlists |
| 4 | Total learners per school per year | enrolment trend feature | **have, 2007–2025, all 9 provinces** | EMIS masterlists |
| 5 | Educators per school per year | teacher:learner ratio | **have, 2007–2025, all 9 provinces** | EMIS masterlists |
| 6 | NSC `Total Wrote` / `% Achieved` per school | pass-rate trend + label fallback | **have, 2010–2024, national** | NSC School Performance Reports |
| 7 | School closure / merge / renumber tracking | data hygiene | **have** | `OldNATEMIS`/`NewNATEMIS` cols |
| 8 | Province-level reasons for leaving | interpreting results | **have** | GHS 2024 |
| 9 | **Learners by grade, per school, per year** | **the dropout label** | **MISSING — gated** | SNAP microdata (DataFirst) |

**One item (#9) is the only real blocker.** Everything else is open and in hand.

---

## Correction to earlier notes

A previous version of this file stated that DBE's EMIS Downloads page "no longer hosts an
ordinary-schools masterlist, only ECD data," and that SNAP registration was required for
teacher-to-learner ratio. **Both are wrong.**

`education.gov.za/Programmes/EMIS/EMISDownloads.aspx` hosts 297 files across 26 quarters
(2013–2025). The provincial files are ordinary schools (`Type_DoE = ORDINARY SCHOOL`) and
each carries `Learners{year}` **and** `Educators{year}`. No login, no registration.

---

## Repo layout

Raw downloads are **gitignored** — several hundred MB, every byte re-fetchable with no
login. The fetch scripts are version controlled instead. Run them to rebuild:

```
src/fetch_emis_masterlists.py   -> datasets/raw/emis_masterlists/   (234 files)
src/fetch_nsc_reports.py        -> datasets/raw/nsc_reports/        (13 PDFs)
src/build_school_panel.py       -> datasets/processed/school_year_panel.csv
```

## What is now downloaded

### `raw/emis_masterlists/` — 233 files, all nine provinces, the backbone
One file per province per quarter. Per school per year: EMIS, name, sector, phase,
district, circuit, quintile, no-fee flag, Section 21, urban/rural, GPS, **learner count,
educator count**.

Years 2007–2013 all sit inside the 2013 Q1 files as `Snap_Learners_2007`…`2013`, so a
single file yields seven years. Then 2015 onward has its own file per quarter.

Two upstream defects to know about:

- **Northern Cape has no 2025 data.** The NC 2025 Q2 slot on DBE's page holds a Word
  document — a School Self-Evaluation form template uploaded into the wrong slot. It
  downloads cleanly with an `.xlsx` extension and is not a spreadsheet. NC's latest is 2024.
- **NC 2019 Q4 returns HTTP 403.** Harmless: that province's Q3 file covers the same year.

### `raw/nsc_reports/` — 13 reports, national, 2012–2024
Each report carries **three years** of results per school, and they chain with no gaps or
overlaps: 2012→(2010-12), 2015→(2013-15), 2018→(2016-18), 2021→(2019-21), 2024→(2022-24).
**Those five alone cover 2010–2024 in full.** Extraction verified with `pdfplumber` on all
five. The 2022 and 2023 editions resist the same parser but are redundant, so it does not
matter.

Per school: EMIS No, Centre No, name, district, quintile, and per year `No Progressed`,
`Total Wrote`, `Total Achieved`, `% Achieved`.

### `processed/school_year_panel.csv.gz` — the model's input
One row per school per year, folded from all 233 masterlists. Committed (gzipped, 7MB;
the plain CSV is 74MB). `pandas.read_csv` opens `.csv.gz` directly.

**478,761 rows — 19 consecutive years, 2007–2025, all nine provinces.**

| Column | Filled |
|---|---|
| learners | 100% |
| phase | 99% |
| quintile | 97% |
| educators | 94% |

184,675 of those rows are secondary or combined schools — the Grade 10–12 population the
model actually targets.

Three defects were found and fixed while building this, none of which raised an error and
all of which would have quietly skewed the trends:

- The 2019 files spell the key column `NatEMIS`, not `NatEmis`. Exact matching dropped the
  entire year. Header matching is now case-insensitive.
- Province codes are unstable — `KZ`/`KZN` and `GT`/`GP` split two provinces in two, so
  the panel reported eleven provinces for a country with nine.
- Gauteng's 2023 file has its key column headed `G`, truncated upstream. 3,000 schools were
  lost. The column is now recovered by inspecting its values rather than its name.

Phase is also absent from the older files under that name (they use `Phase_DoE`), which
left 43% of rows with no phase — and phase is how a secondary school is identified at all.
Stable attributes are now carried across years for the same school.

### `01_DBE_EMIS/` — WCG ArcGIS CSVs (1,480 public + 343 independent)
Weekly-refreshed. Now largely redundant: the masterlists carry GPS, district and quintile
for **all nine provinces**, not just the Western Cape. Keep for medium-of-instruction and
current open/closed status.

### `02_No_Fee_Schools/` — now redundant
Both PDFs parse fine (EMIS, name, phase, address, district, quintile, learner count), but
the masterlists give the same fields for *all* schools across *more* years in clean XLSX.
Keep for cross-checking; don't build the pipeline on them.

### `05_Stats_SA_GHS/GHS_2024_Report.pdf`, `06_Provincial_Data/` — unchanged, sufficient

---

## Join keys — verified, not assumed

EMIS numbers appear with and without a leading zero. Strip non-digits and leading zeros,
then everything matches:

| Join | Match rate |
|---|---|
| ArcGIS CSV → EMIS masterlist 2025 | **1480/1480 (100%)** |
| No-Fee PDF 2023 → EMIS masterlist 2025 | **893/894 (99%)** |
| NSC 2024 PDF (WC pages) → EMIS masterlist 2025 | **463/464 (99%)** |
| EMIS 2024 → EMIS 2025 (year-over-year panel) | **1819 schools** |

Learner *and* educator counts are populated for 1910/1935 WC schools (98.7%) in 2025, so the
teacher:learner ratio is computable now.

---

## The one gap: per-grade enrolment

Grade 10/11/12 counts per school exist **only** in the SNAP microdata. Confirmed licensed on
both mirrors — a free DataFirst account plus a Data Access Agreement, no cost:

- SNAP 1997–2016 (v1.6): https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/689
- SNAP 2023: https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/study/zaf-dbe-snaps-2023-v1
- World Bank mirror (1997–2013, also licensed): https://microdata.worldbank.org/index.php/catalog/2164

Request both SNAP versions from one account.

### Fallback if SNAP does not arrive

Build the label from **matric throughput** instead of cohort tracking: for a secondary
school, compare `Total Wrote` in year Y (NSC) against that school's total enrolment in
year Y−2 (EMIS). This is weaker — it conflates intake changes with dropout, and only works
for schools whose phase is `SECONDARY SCHOOL` — but it is buildable entirely from open data
and needs no registration. State the limitation explicitly if used.

---

## Next steps

1. **You:** register at DataFirst, request SNAP 1997–2016 and SNAP 2023 (item #9).
2. Download NSC School Performance Reports 2012–2021 — each covers 3 years, so ~4 reports
   extend per-school matric history back to 2010. Listed at
   `education.gov.za/Resources/Reports.aspx`.
3. Build the per-school-per-year table from `masterlists/`, keyed on normalised EMIS,
   reconciling renumbering via `OldNATEMIS`/`NewNATEMIS`.
4. Extract NSC tables to CSV and join on EMIS.
5. Engineer features, build the label, train.
