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
| 4 | Total learners per school per year | enrolment trend feature | **have, 2007–2025** | EMIS masterlists |
| 5 | Educators per school per year | teacher:learner ratio | **have, 2007–2025** | EMIS masterlists |
| 6 | NSC `Total Wrote` / `% Achieved` per school | pass-rate trend + label fallback | **2022–24 have; 2012–21 downloadable** | NSC School Performance Reports |
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

## What is now downloaded

### `01_DBE_EMIS/masterlists/` — 35 files, the backbone panel
Western Cape provincial masterlists for every available quarter, plus the national
ordinary-school files. Per school per year: EMIS, name, sector, phase, district, circuit,
quintile, no-fee flag, Section 21, urban/rural, GPS, **learner count, educator count**.

Distinct data years covered for WC: 2007–2013 (all seven inside `WC_2013Q1.xlsx` as
`Snap_Learners_2007`…`2013`), then 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023,
2024, 2025. **2014 is the only gap.**

`WC_2022Q2.xlsx` is mislabelled upstream — its `DataYear` is 2025, not 2022. Trust the
`DataYear` column, not the filename.

### `01_DBE_EMIS/` — WCG ArcGIS CSVs (1,480 public + 343 independent)
Weekly-refreshed, already machine-readable. Redundant with the masterlists for quintile and
identity, but adds medium of instruction and a current open/closed status.

### `04_NSC_Results/NSC_School_Performance_Report_2024.pdf` — 155 pages
Extraction verified with `pdfplumber`. Per school: EMIS No, Centre No, name, district,
quintile, and for **each of 2022, 2023, 2024**: `No Progressed`, `Total Wrote`,
`Total Achieved`, `% Achieved`. Western Cape occupies pages 143–152.

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
