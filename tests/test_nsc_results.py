"""The NSC report parser.

Rows are matched on shape rather than column position, because the number of
empty columns varies from page to page. These tests pin that shape matching,
including the cases that should be rejected - a parser that silently accepts a
header row produces a school called "Centre Name" with a pass rate of nothing.
"""
import pytest

from src.build.nsc_results import parse_row, _row_years, _years_in

YEARS = [2022, 2023, 2024]

# A real row, as pdfplumber returns it: district, EMIS, centre number, name,
# quintile, then four measures for each of three years, padded with the empty
# cells the source table carries.
GOOD_ROW = [
    "CAPE WINELANDS", "", "129333433", "", "1008844", "", "ROODEZANDT SEK.",
    "", "", "", "3", "27", "", "121", "", "83", "68.6", "", "11", "129", "",
    "73", "56.6", "12", "143", "", "100", "69.9",
]


def test_parses_three_years_from_one_row():
    rows = parse_row(GOOD_ROW, YEARS)
    assert len(rows) == 3
    assert [r["year"] for r in rows] == YEARS


def test_reads_the_measures_correctly():
    first = parse_row(GOOD_ROW, YEARS)[0]
    assert first["wrote"] == 121
    assert first["achieved"] == 83
    assert first["pass_rate"] == 68.6
    assert first["progressed"] == 27
    assert first["quintile"] == "3"


def test_normalises_the_identifier():
    # EMIS is published with and without a leading zero; joins depend on this.
    row = list(GOOD_ROW)
    row[2] = "029333433"
    assert parse_row(row, YEARS)[0]["emis"] == "29333433"


def test_carries_the_school_name_across_empty_cells():
    assert parse_row(GOOD_ROW, YEARS)[0]["school"] == "ROODEZANDT SEK."


def test_skips_a_year_with_no_candidates():
    # A school that presented nobody that year has no cohort to measure.
    row = list(GOOD_ROW)
    row[13] = "0"                      # Total Wrote for the first year
    years = [r["year"] for r in parse_row(row, YEARS)]
    assert 2022 not in years and len(years) == 2


def test_rejects_a_header_row():
    header = ["District Name", "EMIS No", "Centre No", "Centre Name",
              "Quintile", "2022", "2023", "2024"]
    assert parse_row(header, YEARS) == []


def test_rejects_a_row_with_no_identifier():
    assert parse_row(["WESTERN CAPE"] + [""] * 20, YEARS) == []


def test_rejects_a_malformed_identifier():
    # Nine digits is the shape; eight is something else.
    row = list(GOOD_ROW)
    row[2] = "12933343"
    assert parse_row(row, YEARS) == []


def test_rejects_a_row_missing_measures():
    assert parse_row(GOOD_ROW[:12], YEARS) == []


def test_finds_years_in_page_text():
    assert _years_in("2022 2023 2024 results") == [2022, 2023, 2024]


def test_year_detection_ignores_numbers_that_are_not_years():
    assert 1008 not in _years_in("Centre 1008844 in 2024")


def test_falls_back_to_the_edition_when_the_page_is_unreadable():
    # An edition reports on its own year and the two before it.
    assert _row_years("no years here", 2024) == [2022, 2023, 2024]


def test_prefers_years_printed_on_the_page_over_the_filename():
    # The 2024 edition reports 2022-2024, so trusting the filename alone would
    # mislabel two thirds of the data.
    assert _row_years("2022 2023 2024", 2024) == [2022, 2023, 2024]
