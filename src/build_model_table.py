"""Reduce the full school-year panel to the rows and columns the model trains on.

The panel holds every school of every type, 2007-2025. The model is about
Grade 10-12 attrition, so only schools whose phase covers those grades matter:
SECONDARY (Gr 8-12) and COMBINED (Gr 1-12). Primary and intermediate schools
have no matric cohort and are dropped.

Also normalises the two fields that are unusable as published:

- Quintile is written "3" in some years and "Q3" in others, plus a literal
  "TO BE UPDATED". Left alone a model reads 3 and Q3 as unrelated categories.
- Learner and educator counts arrive as text and occasionally as junk markers.

Writes datasets/processed/model_table.csv - small enough to open directly.
"""
import os, re, csv, gzip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "datasets", "processed", "school_year_panel.csv.gz")
OUT = os.path.join(ROOT, "datasets", "processed", "model_table.csv")

KEEP_PHASE = ("SECONDARY", "COMBINED")
COLUMNS = ["emis", "year", "province", "school", "phase", "district", "quintile",
           "nofee", "urbanrural", "lat", "lon", "learners", "educators",
           "learner_educator_ratio"]


def quintile(value):
    """'Q3' and '3' are the same school; 'TO BE UPDATED' is not a quintile."""
    m = re.search(r"[1-5]", str(value or ""))
    return m.group(0) if m else ""


def number(value):
    try:
        n = float(str(value).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
    return n if n > 0 else None


def main():
    rows_out, seen = [], set()
    with gzip.open(PANEL, "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            phase = (r["phase"] or "").upper()
            if not any(p in phase for p in KEEP_PHASE):
                continue
            learners = number(r["learners"])
            if learners is None:
                continue
            educators = number(r["educators"])
            rows_out.append({
                "emis": r["emis"], "year": int(r["year"]), "province": r["province"],
                "school": r["school"], "phase": phase, "district": r["district"],
                "quintile": quintile(r["quintile"]), "nofee": r["nofee"],
                "urbanrural": r["urbanrural"], "lat": r["lat"], "lon": r["lon"],
                "learners": int(learners),
                "educators": int(educators) if educators else "",
                "learner_educator_ratio": round(learners / educators, 1) if educators else "",
            })
            seen.add(r["emis"])

    rows_out.sort(key=lambda r: (r["emis"], r["year"]))
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows_out)

    print(f"wrote {OUT}")
    print(f"  {len(rows_out):,} school-year rows   {len(seen):,} distinct schools")
    print(f"  {os.path.getsize(OUT)/1e6:.1f} MB")

    filled = sum(1 for r in rows_out if r["learner_educator_ratio"] != "")
    print(f"  learner:educator ratio present on {100*filled//len(rows_out)}% of rows")


if __name__ == "__main__":
    main()
