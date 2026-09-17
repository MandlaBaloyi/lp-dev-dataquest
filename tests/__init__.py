"""Tests, weighted towards failures that produce no error.

A crash gets noticed. The faults that matter in this project are the ones that
leave a plausible-looking dataset behind: a year silently dropped because its
files spell a column differently, a country gaining two extra provinces because
codes are inconsistent, three thousand schools lost to a truncated header.

Each of those happened. Each left row counts that looked reasonable. They are
pinned here so they cannot return quietly.

    test_emis.py          identifier normalisation, which every join depends on
    test_clean.py         the normalisation rules - every case is a value found
                          in the real source data, not invented
    test_model_table.py   guards on the built table: nine provinces and no
                          more, funding bands normalised, 2019 present
    test_woe.py           weight of evidence, including that transform applies
                          training bins rather than refitting on new data

Run: python -m pytest tests/ -v
"""
