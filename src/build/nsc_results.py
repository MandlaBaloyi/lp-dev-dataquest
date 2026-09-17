"""Extract per-school matric results from the NSC School Performance Reports.

Total Wrote is why this module exists. It counts the candidates a school
presented for matric, which is the numerator of the survival measure the model
is trained on. Without it there is no target.

NO TWO EDITIONS SHARE A LAYOUT

This is the whole difficulty, and it is not visible until you compare them:

    2012   five years, Wrote only, preceded by an unlabelled flag column
    2018   five years, alternating No Progressed and Wrote
    2021   five years, No Progressed and Wrote for each
    2024   five years, No Progressed and Wrote for each

A parser written against any one of them returns nothing at all for the
others - and returns it quietly, since a row that fails to match simply looks
like page furniture. So the layout is read from each report's own header
rather than assumed: every "Wrote 2017" or "No Progressed 2018" encountered
builds the schema for the rows that follow, and the numbers in each data row
are mapped onto it by position.

Years come from the header too, never the filename. An edition named for one
year reports on that year and the four before it, so trusting the name would
mislabel four fifths of the data.

WHY TEXT RATHER THAN TABLE EXTRACTION

pdfplumber's table extraction handles these files but takes over half an hour
across the set and peaks above three gigabytes, because the reports are
hundreds of pages of dense ruled tables. Laying the text out and matching on
shape does the same work in about three seconds per report.

Rows are matched on shape: a nine-digit EMIS number, a seven-digit centre
number, a name, then the numbers. Anything that does not match is a heading,
a subtotal or page furniture, and is skipped.

Writes datasets/processed/nsc_results.csv, one row per school per year.
"""
import csv
import glob
import os
import re
import subprocess
import tempfile

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

# "Total Wrote 2022", "No Progressed 2018", "% Achieved 2024"
HEADER_RE = re.compile(
    r"(No Progressed|Total Wrote|Total Achieved|% Achieved|Wrote|Achieved)\s+(20[0-2]\d)",
    re.I)

# district (optional) + EMIS + centre number + name + numbers
ROW_RE = re.compile(r"^(?P<lead>.*?)(?P<emis>\d{9})\s+(?P<centre>\d{7})\s+(?P<rest>.*)$")

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

# The largest matric cohort any South African school presents is in the low
# hundreds; the 99.9th percentile of everything extracted is 409. Anything
# past this is two columns read as one, not a real figure.
MAX_CANDIDATES = 2000

MEASURE_KEYS = {
    "no progressed": "progressed",
    "total wrote": "wrote",
    "wrote": "wrote",
    "total achieved": "achieved",
    "achieved": "achieved",
    "% achieved": "pass_rate",
}


def to_text(path):
    """Lay the PDF out as text. Far faster than parsing its table structure."""
    handle, out = tempfile.mkstemp(suffix=".txt")
    os.close(handle)
    try:
        subprocess.run(["pdftotext", "-layout", path, out],
                       check=True, capture_output=True)
        with open(out, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    finally:
        os.unlink(out)


def parse_schema(header_lines):
    """Turn header text into the ordered list of (measure, year) the rows carry.

    Deduplicated because the header repeats on every page, and order is what
    lets the numbers in a row be mapped back to what they mean.
    """
    schema, seen = [], set()
    for line in header_lines:
        for measure, year in HEADER_RE.findall(line):
            key = MEASURE_KEYS.get(measure.strip().lower())
            if not key:
                continue
            entry = (key, int(year))
            if entry not in seen:
                seen.add(entry)
                schema.append(entry)
    return schema


def parse_row(line, schema):
    """One text line into school-year records, or nothing if it is not a row."""
    if not schema:
        return []
    match = ROW_RE.match(line)
    if not match:
        return []

    rest = match.group("rest")
    numbers = NUMBER_RE.findall(rest)
    if len(numbers) < len(schema):
        return []

    # Take the measures from the end. Some editions carry an extra unlabelled
    # column between the name and the quintile, and anchoring to the right
    # survives that where counting from the left does not.
    measures = numbers[-len(schema):]
    before = numbers[:-len(schema)]
    quintile = before[-1] if before else ""

    # The name is whatever precedes the first number that belongs to the data.
    name_end = rest.find(before[0] if before else measures[0])
    school = rest[:name_end].strip() if name_end > 0 else rest.strip()
    school = re.sub(r"\s{2,}", " ", school)

    per_year = {}
    for (key, year), value in zip(schema, measures):
        per_year.setdefault(year, {})[key] = value

    district = re.sub(r"\s{2,}", " ", match.group("lead")).strip()
    emis = normalise_emis(match.group("emis"))

    records = []
    for year, values in per_year.items():
        wrote = values.get("wrote")
        if wrote is None or not 0 < float(wrote) <= MAX_CANDIDATES:
            # Zero means the school presented nobody that year. Above the cap
            # means the row's columns did not line up - a value spanning two
            # merged cells rather than a school with more matric candidates
            # than the largest school in the country has learners.
            continue
        records.append({
            "emis": emis, "year": year, "district": district,
            "centre_no": match.group("centre"), "school": school,
            "quintile": quintile,
            "progressed": int(float(values.get("progressed") or 0)),
            "wrote": int(float(wrote)),
            "achieved": int(float(values["achieved"])) if values.get("achieved") else "",
            "pass_rate": float(values["pass_rate"]) if values.get("pass_rate") else "",
        })
    return records


# Order of measures within a year, by how many a report carries. Every edition
# that states its layout uses these, so an edition whose header cannot be read
# is assumed to follow the same convention.
CONVENTIONAL_ORDER = {
    1: ["wrote"],
    2: ["progressed", "wrote"],
    3: ["progressed", "wrote", "achieved"],
    4: ["progressed", "wrote", "achieved", "pass_rate"],
}


def infer_schema(lines, edition, span=5):
    """Work out the layout of a report whose header cannot be read.

    The most recent editions rotate their column headings ninety degrees, so
    laying the page out as text yields no header at all - while the data rows
    below are perfectly legible. Rather than lose the only years that matter
    for testing, the layout is inferred: an edition reports on its own year and
    the four before it, and the count of numbers in a row reveals how many
    measures each year carries.
    """
    counts = {}
    for line in lines:
        match = ROW_RE.match(line)
        if not match:
            continue
        found = len(NUMBER_RE.findall(match.group("rest")))
        counts[found] = counts.get(found, 0) + 1
    if not counts:
        return []

    # The most common row width, ignoring rows with stray or missing cells.
    width = max(counts, key=counts.get)
    per_year = (width - 1) // span            # less one for the quintile
    order = CONVENTIONAL_ORDER.get(per_year)
    if not order:
        return []

    years = list(range(edition - span + 1, edition + 1))
    return [(measure, year) for year in years for measure in order]


def extract(path):
    """Every school-year record in one report."""
    text = to_text(path)
    lines = text.splitlines()
    out, province, schema, pending = [], "", [], []

    # Editions with rotated headings produce no readable header, so the layout
    # is inferred from the rows themselves before parsing begins.
    if not any(HEADER_RE.search(line) for line in lines):
        edition = int(re.search(r"(20\d{2})", os.path.basename(path)).group(1))
        schema = infer_schema(lines, edition)
        if schema:
            print(f"    inferred layout for {os.path.basename(path)}: "
                  f"{len(schema) // 5} measures x 5 years")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        upper = stripped.upper()
        for name, code in PROVINCES.items():
            if name in upper and len(stripped) < 60:
                province = code
                break

        if HEADER_RE.search(stripped):
            pending.append(stripped)
            continue

        records = parse_row(line, schema)
        if not records and pending:
            # A header block has just ended; adopt it before the rows below.
            schema = parse_schema(pending)
            pending = []
            records = parse_row(line, schema)

        for record in records:
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
    # figures are restated when a school's results are corrected.
    combined = {}
    for path in files:
        try:
            records = extract(path)
        except Exception as exc:
            print(f"  {os.path.basename(path):40} FAILED  {type(exc).__name__}: {exc}")
            continue
        for record in records:
            combined[(record["emis"], record["year"])] = record
        years = sorted({r["year"] for r in records})
        span = f"{years[0]}-{years[-1]}" if years else "none"
        print(f"  {os.path.basename(path):40} {len(records):>7,} rows  {span}")

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
