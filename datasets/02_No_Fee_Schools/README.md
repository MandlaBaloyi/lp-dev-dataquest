# DBE "No Fee Schools" Lists (Provincial, by Year)

## ✅ What's actually in this folder (downloaded 2026-09-16)

### `WC_No_Fee_Schools_2023.pdf` (875 KB)
### `WC_No_Fee_Schools_2025.pdf` (953 KB)

Both downloaded directly, no login required, from DBE's own publications archive:
- 2023: https://www.education.gov.za/Portals/0/Documents/Publications/2023%20No%20Fee%20Schools/WC%20No%20Fee%20Schools%202023%20list.pdf
- 2025: https://www.education.gov.za/Portals/0/Documents/Publications/2023/WC%20No%20Fee%20Schools%202025%20list.pdf

**Contents (per the DBE publication):** school name, phase, address, education district, quintile (NQ1-NQ5), and learner numbers, for every no-fee school in the Western Cape, for that year.

### ⚠️ Confirmed limitation (checked 2026-09-16 via `pdftotext -layout`)
The "learner numbers" column is a **single total per school** — it is NOT broken down by grade. This closes off the hope (raised in `docs/plan_v1.txt` Section 2) that this file could supply Grade 10/11/12-specific enrollment counts. It's still usable for a rough whole-school enrollment trend (2023 vs 2025) and as a cross-check on quintile, but it cannot supply the denominator needed for a true cohort-tracked dropout % label. The only remaining candidate for that is the SNAP Survey (`03_SNAP_Survey/`), still pending DataFirst registration.

These are genuine PDFs — they still need to be converted to a clean table (they're not pre-structured CSVs). See "Turning these into usable data" below.

## Better alternative already in `01_DBE_EMIS/`
The `WesternCape_Public_Ordinary_Schools_2025.csv` file in the `01_DBE_EMIS` folder already has a `QUINTILES` and `NOFEESCHOOL` (Y/N) column for **all 1,480** public schools in the province — not just the no-fee ones — pulled from a live, structured API rather than a PDF. For quintile/no-fee status alone, that CSV is easier to use than parsing these PDFs.

**What these PDFs still add that the CSV doesn't:** year-by-year learner headcounts (needed to calculate enrollment trend, per Section 3(b) of the plan). The CSV is a live current snapshot; it doesn't give you historical learner counts per year.

## Turning these PDFs into usable data
To extract the tables:
1. Try `pdftotext -layout WC_No_Fee_Schools_2023.pdf out.txt` then parse with a script, OR
2. Use a PDF table-extraction tool (e.g. `camelot`, `tabula-py`, or Excel's "Get Data from PDF"), OR
3. Ask me to do this — I can extract and clean these into CSV once you confirm this is the next step.

## ⚠️ Still missing
- **No Fee Schools lists for other provinces** (Eastern Cape 2025 was also found and can be pulled the same way — ask if you want it downloaded)
- **Earlier years** (2019-2022) for Western Cape — DBE's archive structure changes URL patterns by year, so these need to be searched for individually. Not yet downloaded.
