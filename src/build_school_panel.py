"""Fold every provincial EMIS masterlist into one school-year panel.

Reads datasets/raw/emis_masterlists/*.xlsx and writes
datasets/processed/school_year_panel.csv - one row per school per year.

Five things make this less trivial than it sounds:

1. Column names drift year to year. Learner counts appear as Learners2025,
   Learners_2015, "Learner_Number 2017" and Snap_Learners_2011. We match any
   column whose name mentions learners/educators and ends in a four-digit year.

2. Capitalisation drifts too. The 2019 files say NatEMIS where every other year
   says NatEmis. All header matching is therefore case-insensitive - an exact
   match silently dropped the whole of 2019 on the first run.

3. Province codes are not stable: KwaZulu-Natal appears as both KZ and KZN, and
   Gauteng as both GT and GP, which splits one province into two.

4. Some files carry several years at once. The 2013 Q1 files hold
   Snap_Learners_2007 through 2013, so one row there yields seven panel rows.

5. The same year is published in several quarters. Later quarters supersede
   earlier ones, so we keep the highest quarter seen for each school-year.

Known source-side defect: the Northern Cape 2025 Q2 slot on DBE's page holds a
Word template, not a masterlist, so NC has no 2025 row. Nothing to fix our end.
"""

import os
import re
import csv
import gzip
import glob
import itertools
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "datasets", "raw", "emis_masterlists")
OUT_DIR = os.path.join(ROOT, "datasets", "processed")
# Gzipped: the plain CSV is ~74MB, which is past the point where GitHub starts
# complaining. pandas.read_csv reads .csv.gz directly, no extra step needed.
OUT = os.path.join(OUT_DIR, "school_year_panel.csv.gz")

# Preferred column name first; the first one present in a file wins.
FIELDS = {
    "province":  ["Province"],
    "school":    ["Official_Institution_Name", "Institution_Name", "InstitutionName",
                  "LURITS_Name", "Name"],
    "status":    ["Status", "DoE_Status"],
    "sector":    ["Sector"],
    "type":      ["Type_DoE", "Type"],
    "phase":     ["Phase_PED", "Phase_DoE", "Phase"],
    "district":  ["EIDistrict", "EI_District"],
    "circuit":   ["EICircuit"],
    "quintile":  ["Quintile"],
    "nofee":     ["NoFeeSchool"],
    "urbanrural": ["Urban_Rural", "UrbanRural"],
    "lat":       ["GIS_Lat", "GIS_Latitude", "New Lat"],
    "lon":       ["GIS_Long", "GIS_Longitude", "New Long"],
    "old_emis":  ["OldNATEMIS"],
    "new_emis":  ["NewNATEMIS"],
}

# The same province is published under different codes in different years.
PROVINCE_FIX = {"KZ": "KZN", "GT": "GP", "NC": "NC", "NW": "NW"}

COLUMNS = ["emis", "year", "province", "school", "status", "sector", "type", "phase",
           "district", "circuit", "quintile", "nofee", "urbanrural", "lat", "lon",
           "old_emis", "new_emis", "learners", "educators", "source_file"]


def norm_emis(value):
    """EMIS is published with and without a leading zero; strip to compare."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.lstrip("0")


def clean(value):
    text = str(value).strip() if value is not None else ""
    return "" if text in (".", "99", "N/A", "UNKNOWN", "None") else text


def year_columns(header, word):
    """Map {year: column index} for any column naming `word` and a year."""
    out = {}
    for i, name in enumerate(header):
        if word in name.lower():
            m = re.search(r"(20\d{2})", name)
            if m:
                out[int(m.group(1))] = i
    return out


def find_col(header, candidates):
    """Case-insensitive header lookup. 2019 spells it NatEMIS, not NatEmis."""
    lowered = [h.strip().lower() for h in header]
    for cand in candidates:
        try:
            return lowered.index(cand.strip().lower())
        except ValueError:
            continue
    return None


def looks_like_emis(values):
    """EMIS numbers are 8-10 digit integers. Used to recover a mislabelled column."""
    hits = [v for v in values if re.fullmatch(r"0?\d{8,10}", str(v or "").strip())]
    return len(hits) >= max(3, len(values) // 2)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(RAW, "*.xlsx")))
    print(f"reading {len(files)} masterlists\n")

    # (emis, year) -> (quarter_rank, row) so later quarters win
    panel = {}
    skipped = []

    for path in files:
        fname = os.path.basename(path)
        m = re.match(r"([A-Z]+)_(\d{4})Q(\d)\.xlsx$", fname)
        rank = (int(m.group(2)), int(m.group(3))) if m else (0, 0)
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            skipped.append((fname, str(exc)[:50]))
            continue

        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            try:
                header = [str(c or "") for c in next(rows)]
            except StopIteration:
                continue
            i_emis = find_col(header, ["NatEmis", "NatEMIS", "NATEMIS"])
            if i_emis is None:
                # Gauteng 2023 ships with its first column headed "G" - the header
                # was truncated upstream. Recover it by checking the values.
                peek = list(itertools.islice(rows, 8))
                rows = itertools.chain(peek, rows)
                if peek and looks_like_emis([r[0] for r in peek if r]):
                    i_emis = 0
                    print(f"  recovered mislabelled EMIS column in {fname} "
                          f"(header was {header[0]!r})")
                else:
                    continue

            learner_cols = year_columns(header, "learner")
            educator_cols = year_columns(header, "educator")
            if not learner_cols:
                continue

            resolved = {k: find_col(header, c) for k, c in FIELDS.items()}

            for row in rows:
                emis = norm_emis(row[i_emis])
                if not emis:
                    continue
                base = {k: clean(row[i]) if i is not None and i < len(row) else ""
                        for k, i in resolved.items()}
                prov = base["province"].strip().upper()
                base["province"] = PROVINCE_FIX.get(prov, prov)

                for year, li in learner_cols.items():
                    learners = row[li] if li < len(row) else None
                    if learners in (None, "", ".", "99"):
                        continue
                    ei = educator_cols.get(year)
                    educators = row[ei] if ei is not None and ei < len(row) else None

                    key = (emis, year)
                    if key in panel and panel[key][0] >= rank:
                        continue
                    rec = dict(base)
                    rec.update(emis=emis, year=year, learners=learners,
                               educators=educators if educators not in (".", "99") else "",
                               source_file=fname)
                    panel[key] = (rank, rec)
        wb.close()

    print(f"panel rows: {len(panel)}")

    # A school's phase, sector and name do not change year to year, but the older
    # files record them under different column names and sometimes not at all.
    # Carry the known value across every year of the same school.
    STABLE = ("phase", "sector", "type", "school", "district", "urbanrural", "lat", "lon")
    known = {}
    for _, rec in panel.values():
        slot = known.setdefault(rec["emis"], {})
        for field in STABLE:
            if not slot.get(field) and rec.get(field):
                slot[field] = rec[field]
    filled = 0
    for _, rec in panel.values():
        for field in STABLE:
            if not rec.get(field) and known[rec["emis"]].get(field):
                rec[field] = known[rec["emis"]][field]
                filled += 1
    print(f"back-filled {filled} stable attribute values across years")

    with gzip.open(OUT, "wt", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for _, rec in sorted(panel.values(), key=lambda kv: (kv[1]["emis"], kv[1]["year"])):
            w.writerow(rec)

    years, provs = {}, {}
    for _, rec in panel.values():
        years[rec["year"]] = years.get(rec["year"], 0) + 1
        p = rec["province"] or "?"
        provs[p] = provs.get(p, 0) + 1

    print(f"\nwrote {OUT}")
    print(f"\n{'year':>6} {'schools':>9}")
    for y in sorted(years):
        print(f"{y:>6} {years[y]:>9}")
    print(f"\n{'province':>10} {'rows':>9}")
    for p in sorted(provs, key=lambda k: -provs[k]):
        print(f"{p:>10} {provs[p]:>9}")
    for fname, why in skipped:
        print(f"  SKIPPED {fname}: {why}")


if __name__ == "__main__":
    main()
