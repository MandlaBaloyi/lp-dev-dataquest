# `datasets/raw/` — the original source files, as published

**These are the untouched government files this project is built from.**
Nothing here has been edited, cleaned or reformatted. Every number in the app
traces back to one of them.

They are committed so the work can be checked rather than taken on trust. The
alternative — "run our fetch script and assume the department still serves the
same file" — is weaker, and for the NSC reports it is not good enough at all:
we extracted those tables ourselves because no machine-readable version exists,
so without the PDFs the extraction cannot be independently verified.

## What is here

| Folder | Contents | Source |
|---|---|---|
| `nsc_reports/` | **13 of 13.** NSC School Performance Reports, 2008–2024. 98 MB. The source for every matric figure in the project. | [education.gov.za › Reports](https://www.education.gov.za/Resources/Reports.aspx) |
| `emis_masterlists/` | **4 of 140.** Provincial school masterlists, quarterly, 2007–2025. See the note below. | [education.gov.za › EMIS Downloads](https://www.education.gov.za/Programmes/EMIS/EMISDownloads.aspx) |

No login, no licence, no NDA, no API key. Both sets are published openly by the
Department of Basic Education.

### The masterlists are incomplete, and that is stated rather than hidden

The enrolment panel was built from **140** provincial spreadsheets. Four remain
in this folder; the rest were cleared during development to save disk space.
The built tables in `datasets/processed/` were produced from the full set and
are committed in full, so nothing downstream is missing — but the complete raw
input is not here.

To restore it:

```bash
python -m src.fetch.emis_masterlists
```

The script reads the department's download page and retrieves what is currently
published, validating each file's magic bytes before writing it.

## Rebuilding everything from these files

```bash
python -m src.build.nsc_results        # PDFs   -> nsc_results.csv
python -m src.build.school_panel       # sheets -> school_year_panel.csv.gz
python -m src.build.clean              #        -> clean_panel.csv.gz
python -m src.model.features           #        -> model_frame.csv.gz
python -m src.model.train              # the scorecard -> outputs/
```

Run from the repository root. Running a file by path breaks the `src.` imports.

**You do not need to run any of this to use the project.** The built tables are
committed, so the app works immediately after a clone:

```bash
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

**One caveat, stated because it is true:** the fetch scripts retrieve what the
department publishes *today*. If a file has been revised or withdrawn since the
committed tables were built, a rebuild will not reproduce them byte for byte.
That is a property of a live government portal, not a defect here, and it is
the second reason these originals are committed rather than only the recipe.

## Why these files are worth reading directly

The NSC PDFs are where our own worst bug lived. The first parser trusted each
report's header as the layout for the whole file; the reports mix layouts
between sections. It produced 14,005 records claiming more learners were
advanced into matric than sat the exam, and silently destroyed the pass-rate
column. Open `NSC_School_Performance_2018.pdf` and the mixed layouts are
visible on the page.

The fix is verified by arithmetic the source itself prints: where a report
gives both the achieved count and the pass rate, the rate must equal achieved ÷
wrote. It holds on 82,979 of 82,979 checkable records — a check anyone can
repeat against these files.

Full provenance is in `docs/DATASETS.txt`; every column and its measured fill
rate is in `docs/DATA_DICTIONARY.txt`; reference material on every source we
considered, including the ones we could not use, is in `datasets/sources/`.
