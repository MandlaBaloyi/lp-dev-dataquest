"""EMIS normalisation - the key every join in this project depends on."""
from src.common.emis import normalise, looks_like_emis


def test_leading_zero_is_stripped():
    # The same school, published two ways across two sources.
    assert normalise("0100000217") == normalise("100000217")


def test_handles_whitespace_and_non_digits():
    assert normalise(" 0100000217 ") == "100000217"
    assert normalise("100-000-217") == "100000217"


def test_empty_input_does_not_crash():
    assert normalise(None) == ""
    assert normalise("") == ""


def test_recognises_a_column_of_emis_numbers():
    # Gauteng 2023 ships its key column headed "G"; recovery relies on this.
    assert looks_like_emis(["0100000217", "100000218", "600101801"])


def test_rejects_a_column_that_is_not_emis_numbers():
    assert not looks_like_emis(["PRIMARY SCHOOL", "URBAN", "Q3"])
