"""Stage 1 - download raw data from public sources.

    emis_masterlists.py   234 provincial school spreadsheets, one per
                          province per quarter
    nsc_reports.py        13 matric performance reports, each carrying three
                          years of results

These scripts are version controlled; their output is not. The downloads run
to several hundred megabytes and every byte is re-fetchable without a login,
so committing the scripts instead keeps the repository clonable and guarantees
anyone can rebuild the exact same inputs.

Both scripts discover what to download by reading the source page rather than
holding hardcoded links, so a newly published quarter is picked up without a
code change. Both verify file signatures before writing - a government site
returning an HTML error page under a spreadsheet filename is a real failure
mode, and one that otherwise surfaces much later as an unreadable file.

Both are safe to re-run. Files already present are skipped.
"""
