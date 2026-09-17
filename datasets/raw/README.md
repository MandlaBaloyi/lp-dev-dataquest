# `datasets/raw/` — intentionally empty on GitHub

**The raw source data is not committed. This is deliberate, not an omission.**

If you are looking for the data this project runs on, you do not need this
folder: **the built tables are committed** in `datasets/processed/`, so the app
and the model run immediately after a clone with nothing downloaded.

```bash
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

## Why it is not here

| | |
|---|---|
| **Size** | ~100 MB+ of provincial spreadsheets and PDF reports. GitHub rejects any single file over 100 MB and this would dominate the repository. |
| **It is not ours** | Every file is published by the Department of Basic Education. Committing them copies someone else's payload into our repository for no gain. |
| **The scripts are better than the payload** | The fetch scripts read the department's live download pages, so they retrieve whatever is currently published rather than a snapshot that silently ages. |

## What belongs here, and how to get it

```bash
python -m src.fetch.emis_masterlists   # -> datasets/raw/emis_masterlists/
python -m src.fetch.nsc_reports        # -> datasets/raw/nsc_reports/
```

| Folder | Contents | Source |
|---|---|---|
| `emis_masterlists/` | Provincial school masterlists, `.xlsx`, quarterly, 2007–2025, all 9 provinces. 140 files feed the built panel. | [education.gov.za › EMIS Downloads](https://www.education.gov.za/Programmes/EMIS/EMISDownloads.aspx) |
| `nsc_reports/` | NSC School Performance Reports, `.pdf`, 13 editions, 2008–2024. | [education.gov.za › Reports](https://www.education.gov.za/Resources/Reports.aspx) |

No login, no licence, no NDA, no API key. Both scripts validate what they
receive against the format's magic bytes before writing it, because these
portals return HTML error pages under a spreadsheet's filename often enough to
matter.

## Rebuilding everything from scratch

```bash
python -m src.fetch.emis_masterlists   # download the spreadsheets
python -m src.fetch.nsc_reports        # download the PDFs
python -m src.build.nsc_results        # PDFs   -> nsc_results.csv
python -m src.build.school_panel       # sheets -> school_year_panel.csv.gz
python -m src.build.clean              #        -> clean_panel.csv.gz
python -m src.model.features           #        -> model_frame.csv.gz
python -m src.model.train              # the scorecard -> outputs/
```

Run from the repository root. Running a file by path breaks the `src.` imports.

**One caveat, stated because it is true:** these scripts fetch what the
department publishes *today*. If a file has been revised or withdrawn since we
built the committed tables, a rebuild will not reproduce them byte for byte.
That is a property of scraping a live government portal, not a defect here, and
it is exactly why the built tables are committed rather than only the recipe.

Full provenance is in `docs/DATASETS.txt`; every column and its fill rate is in
`docs/DATA_DICTIONARY.txt`; reference material on every source we considered,
including the ones we could not use, is in `datasets/sources/`.
