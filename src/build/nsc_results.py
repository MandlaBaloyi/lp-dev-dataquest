"""Extract per-school matric results from the NSC School Performance Report PDFs.

Each report carries three years of results for every school that wrote the
exam, and the editions chain without gaps: 2012 covers 2010-2012, 2015 covers
2013-2015, and so on. Five reports therefore cover 2010-2024 completely.

Per school per year the reports give:

    Progressed No     learners advanced into matric without having met the
                      promotion requirements
    Total Wrote       candidates who sat the exam - the closest available
                      measure of how many of a cohort reached the end
    Total Achieved    candidates who passed
    % Achieved        pass rate

Total Wrote is why this module exists. It is the numerator of the survival
measure the model is trained on; without it there is no target.

Two things make the extraction awkward:

1. The year headers are rotated 90 degrees in the source, so pdfplumber
   returns them reversed - "Quintile" arrives as "elitniuQ". Years are read
   from the raw header text, which survives reversal because a four-digit year
   is a palindrome-safe token to search for.

2. The tables carry many empty columns, and a school's district is printed
   once and left blank on following rows. Empty cells are dropped and the
   district carried forward.

Rather than trusting column positions, each row is matched on shape: a 9-digit
EMIS number, a 7-digit centre number, a name, then a quintile and twelve
numbers - four measures across three years. Anything not matching that shape
is a header, a page furniture row, or a subtotal, and is skipped.

Writes datasets/processed/nsc_results.csv, one row per school per year.
"""
import csv
import glob
import os
import re

import pdfplumber

from src.common.emis import normalise as normalise_emis
from src.common.paths import NSC_RAW, NSC_TABLE, PROCESSED, ensure

PROVINCES = {
    "EASTERN CAPE": "EC", "FREE STATE": "FS", "GAUTENG": "GP",
    "KWAZULU-NATAL": "KZN", "KWAZULU NATAL": "KZN", "LIMPOPO": "LP",
    "MPUMALANGA": "MP", "NORTH WEST": "NW", "NORTHERN CAPE": "NC",
    "WESTERN CAPE": "WC",
}

COLUMNS = ["emis", "year", "province", "district", "centre_no", "school",
           "quintile", "progressed", "wrote", "achieved", "pass_rate",
           "source_file"]

EMIS_RE = re.compile(r"^\d{9}$")
CENTRE_RE = re.compile(r"^\d{7}$")
NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")


def _clean(cell):
    """Flatten a table cell to a single-line string."""
    return re.sub(r"\s+", " ", str(cell or "")).strip()


def _maybe_reversed(text):
    """Header text arrives reversed because the source rotates it 90 degrees."""
    return text[::-1]


def _years_in(text):
    """Every four-digit year mentioned, in order, deduplicated."""
    found = []
    for year in re.findall(r"\b(20[0-2]\d)\b", text):
        value = int(year)
        if value not in found:
            found.append(value)
    return found


def _row_years(page_text, fallback):
    """The three years this page reports on.

    Read from the page rather than the filename: an edition named for one year
    reports on that year and the two before it, and trusting the name would
    mislabel two thirds of the data.
    """
    years = [y for y in _years_in(page_text) if 2009 < y <= fallback]
    tail = sorted(set(years))[-3:]
    return tail if len(tail) == 3 else [fallback - 2, fallback - 1, fallback]


def parse_row(cells, years):
    """One table row into up to three school-year records, or nothing.

    Matched on shape rather than column position, because the number of empty
    columns varies between pages.
    """
    values = [c for c in (_clean(x) for x in cells) if c]
    if len(values) < 16:
        return []

    emis_at = next((i for i, v in enumerate(values) if EMIS_RE.match(v)), None)
    if emis_at is None:
        return []
    if emis_at + 1 >= len(values) or not CENTRE_RE.match(values[emis_at + 1]):
        return []

    district = " ".join(values[:emis_at]) if emis_at else ""
    emis = values[emis_at]
    centre = values[emis_at + 1]

    rest = values[emis_at + 2:]
    numbers_at = next((i for i, v in enumerate(rest) if NUMBER_RE.match(v)), None)
    if numbers_at is None:
        return []

    school = " ".join(rest[:numbers_at]).strip()
    numbers = [v for v in rest[numbers_at:] if NUMBER_RE.match(v)]

    # quintile, then four measures for each of three years
    if len(numbers) < 13:
        return []
    quintile, measures = numbers[0], numbers[1:13]

    records = []
    for index, year in enumerate(years):
        progressed, wrote, achieved, rate = measures[index * 4:(index + 1) * 4]
        if not wrote or float(wrote) <= 0:
            continue                      # school did not present candidates
        records.append({
            "emis": normalise_emis(emis), "year": year, "district": district,
            "centre_no": centre, "school": school, "quintile": quintile,
            "progressed": int(float(progressed)), "wrote": int(float(wrote)),
            "achieved": int(float(achieved)), "pass_rate": float(rate),
        })
    return records


def extract(path):
    """Every school-year record in one report."""
    edition = int(re.search(r"(20\d{2})", os.path.basename(path)).group(1))
    out, province = [], ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Province headings appear both upright and rotated.
            for name, code in PROVINCES.items():
                if name in text.upper() or name in _maybe_reversed(text).upper():
                    province = code
                    break
            if not province:
                continue

            years = _row_years(text, edition)
            for table in page.extract_tables():
                for row in table:
                    for record in parse_row(row, years):
                        record["province"] = province
                        record["source_file"] = os.path.basename(path)
                        out.append(record)
    return out


def main():
    ensure(PROCESSED)
    files = sorted(glob.glob(os.path.join(NSC_RAW, "*.pdf")))
    if not files:
        raise SystemExit(
            f"No reports in {NSC_RAW}. Run: python -m src.fetch.nsc_reports")

    print(f"reading {len(files)} reports\n")

    # (emis, year) -> record. Later editions supersede earlier ones, since
    # results are restated when a school's figures are corrected.
    combined = {}
    for path in files:
        try:
            records = extract(path)
        except Exception as exc:
            print(f"  {os.path.basename(path):40} FAILED  {type(exc).__name__}")
            continue
        for record in records:
            combined[(record["emis"], record["year"])] = record
        years = sorted({r["year"] for r in records})
        span = f"{years[0]}-{years[-1]}" if years else "none"
        print(f"  {os.path.basename(path):40} {len(records):>6,} rows  {span}")

    rows = sorted(combined.values(), key=lambda r: (r["emis"], r["year"]))
    with open(NSC_TABLE, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nwrote {NSC_TABLE}")
    print(f"  {len(rows):,} school-year rows   "
          f"{len({r['emis'] for r in rows}):,} schools")

    by_year = {}
    for record in rows:
        by_year[record["year"]] = by_year.get(record["year"], 0) + 1
    print(f"\n{'year':>6} {'schools':>9}")
    for year in sorted(by_year):
        print(f"{year:>6} {by_year[year]:>9,}")


if __name__ == "__main__":
    main()
