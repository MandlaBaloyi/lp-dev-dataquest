"""Run the anomaly detectors over both datasets and write the findings.

    python -m src.eda.run_audit

Produces outputs/data_audit.csv and outputs/data_audit_summary.json, which the
Data audit page reads. This existed as an ad-hoc script for a while, which
meant the app depended on two files nothing in the repository could rebuild -
clone it, run the pipeline, and the page that answers the challenge would have
had nothing to show.

Both datasets are audited on the same terms. The matric results get their own
detectors rather than the enrolment ones reused, because they are a different
shape - counts of exam candidates, not a school roll - and reusing the wrong
detector produces findings phrased about the wrong thing.
"""
import json

import pandas as pd

from src.common.data import load_nsc, load_panel
from src.common.paths import out
from src.eda import anomalies

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def run():
    panel = load_panel()
    nsc = load_nsc()

    enrolment = anomalies.scan(panel)
    enrolment["dataset"] = "Enrolment masterlists"

    matric = anomalies.matric_scan(nsc)
    matric["dataset"] = "Matric results"

    findings = pd.concat([enrolment, matric], ignore_index=True)
    findings["_rank"] = findings["severity"].map(SEVERITY_ORDER)
    findings = (findings.sort_values(["_rank", "schools_affected"],
                                     ascending=[True, False])
                .drop(columns="_rank").reset_index(drop=True))
    findings.to_csv(out("data_audit.csv"), index=False)

    summary = anomalies.summary(findings)
    summary.update(
        datasets=2,
        records_scanned=len(panel) + len(nsc),
        enrolment_records=len(panel),
        matric_records=len(nsc),
        schools_scanned=int(panel["emis"].nunique()),
        matric_schools=int(nsc["emis"].nunique()),
        years_scanned=int(panel["year"].nunique()),
        provinces_scanned=int(panel["province"].nunique()),
    )

    # The national totals behind the 2017 chart, so the page does not have to
    # reopen a 478,761-row panel to draw one line.
    totals = panel.copy()
    totals["year"] = pd.to_numeric(totals["year"], errors="coerce")
    totals["learners"] = pd.to_numeric(totals["learners"], errors="coerce")
    by_year = (totals.dropna(subset=["year", "learners"])
               .groupby("year")["learners"].sum())
    summary["national_totals"] = {int(y): int(v) for y, v in by_year.items()}

    with open(out("data_audit_summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(f"audited {summary['datasets']} datasets, "
          f"{summary['records_scanned']:,} records")
    print(f"  {summary['total_findings']} findings "
          f"({summary['high']} high, {summary['medium']} medium, {summary['low']} low)")
    print(f"  wrote {out('data_audit.csv')}")
    print(f"  wrote {out('data_audit_summary.json')}")
    return findings, summary


if __name__ == "__main__":
    run()
