"""The NSC report parser.

No two editions of the report share a layout, so the parser reads each one's
own header and maps the numbers in a row onto it. These tests cover both that
path and the fallback used for editions whose headings are rotated in the
source and therefore unreadable as text.

The rejection cases matter as much as the parsing ones. A parser that quietly
accepts a header row invents a school called "Centre Name", and nothing about
that raises an error.
"""
import pytest

from src.build.nsc_results import (CONVENTIONAL_ORDER, infer_schema,
                                   parse_row, parse_schema)

# As the 2021 edition prints it: five years, two measures each.
HEADER_2021 = [
    "No Progressed 2017", "Wrote 2017", "No Progressed 2018", "Wrote 2018",
    "No Progressed 2019", "Wrote 2019", "No Progressed 2020", "Wrote 2020",
    "No Progressed 2021", "Wrote 2021",
]

ROW_2021 = ("Nelson Mandela  200100131  4341014 COLLEGIATE GIRLS HIGH SCHOOL"
            "                  5 0 125 0 135 0 156 0 126 0 134")


def test_reads_the_layout_from_the_header():
    schema = parse_schema(HEADER_2021)
    assert len(schema) == 10
    assert schema[0] == ("progressed", 2017)
    assert schema[1] == ("wrote", 2017)
    assert schema[-1] == ("wrote", 2021)


def test_header_repeats_are_collapsed():
    # The header reprints on every page; the layout must not grow each time.
    assert parse_schema(HEADER_2021 * 4) == parse_schema(HEADER_2021)


def test_parses_five_years_from_one_row():
    rows = parse_row(ROW_2021, parse_schema(HEADER_2021))
    assert [r["year"] for r in rows] == [2017, 2018, 2019, 2020, 2021]
    assert [r["wrote"] for r in rows] == [125, 135, 156, 126, 134]


def test_takes_the_identifier_and_name():
    first = parse_row(ROW_2021, parse_schema(HEADER_2021))[0]
    assert first["emis"] == "200100131"
    assert first["centre_no"] == "4341014"
    assert "COLLEGIATE" in first["school"]


def test_normalises_a_leading_zero_in_the_identifier():
    # EMIS is published both ways across sources, and every join depends on it.
    row = ROW_2021.replace("200100131", "000100131")
    assert parse_row(row, parse_schema(HEADER_2021))[0]["emis"] == "100131"


def test_skips_a_year_the_school_presented_nobody():
    row = ROW_2021.replace("5 0 125", "5 0 0")
    years = [r["year"] for r in parse_row(row, parse_schema(HEADER_2021))]
    assert 2017 not in years and len(years) == 4


def test_rejects_an_impossible_candidate_count():
    # Columns that fail to line up produce a value spanning two merged cells.
    # The largest real matric cohort is in the low hundreds.
    row = ROW_2021.replace("0 125", "0 606080106")
    years = [r["year"] for r in parse_row(row, parse_schema(HEADER_2021))]
    assert 2017 not in years


def test_rejects_a_row_without_an_identifier():
    assert parse_row("WESTERN CAPE", parse_schema(HEADER_2021)) == []


def test_rejects_a_row_with_too_few_numbers():
    assert parse_row("Metro  200100131  4341014 SOME SCHOOL  5 0 125",
                     parse_schema(HEADER_2021)) == []


def test_parses_nothing_without_a_layout():
    assert parse_row(ROW_2021, []) == []


def test_infers_the_layout_when_the_header_cannot_be_read():
    # The recent editions rotate their headings, so text extraction yields no
    # header at all while the rows below remain perfectly legible.
    lines = [ROW_2021] * 5
    schema = infer_schema(lines, edition=2021, span=5)
    assert len(schema) == 10
    assert schema[1] == ("wrote", 2017)
    assert schema[-1] == ("wrote", 2021)


def test_inferred_layout_parses_the_same_values_as_the_header():
    from_header = parse_row(ROW_2021, parse_schema(HEADER_2021))
    inferred = parse_row(ROW_2021, infer_schema([ROW_2021] * 5, 2021, 5))
    assert [r["wrote"] for r in from_header] == [r["wrote"] for r in inferred]


def test_inference_returns_nothing_when_there_are_no_rows():
    assert infer_schema(["WESTERN CAPE", "District Name"], 2024) == []


def test_measure_order_puts_wrote_after_progressed():
    # Wrote is the figure the model depends on, so its position must be right.
    assert CONVENTIONAL_ORDER[2] == ["progressed", "wrote"]
    assert CONVENTIONAL_ORDER[4][1] == "wrote"
