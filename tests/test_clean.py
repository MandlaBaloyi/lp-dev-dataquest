"""The normalisation rules.

Each case here is a real value found in the source data, not invented.
"""
from src.features import clean


def test_phase_variants_collapse():
    for raw in ["SECONDARY SCHOOL", "Secondary School", "Secondary", "SECONDARY"]:
        assert clean.phase(raw) == "SECONDARY"


def test_quintile_accepts_every_published_form():
    assert clean.quintile("3") == "3"
    assert clean.quintile("Q3") == "3"
    assert clean.quintile("NQ2") == "2"


def test_quintile_rejects_non_values():
    for raw in ["TO BE UPDATED", "NOT APPLICABLE", "NULL", ""]:
        assert clean.quintile(raw) == clean.UNKNOWN


def test_nofee_collapses_twelve_spellings_to_two():
    for raw in ["YES", "Y", "No Fee"]:
        assert clean.nofee(raw) == "NO_FEE"
    for raw in ["NO", "N", "Fee Charging", "Fee Paying", "Free Charging"]:
        assert clean.nofee(raw) == "FEE_CHARGING"


def test_urbanrural_keeps_deep_rural_distinct():
    assert clean.urbanrural("RURAL") == "RURAL"
    assert clean.urbanrural("DEEP RURAL") == "DEEP_RURAL"
    assert clean.urbanrural("urban") == "URBAN"


def test_status_treats_operational_as_open():
    assert clean.status("OPEN") == "OPEN"
    assert clean.status("OPERATIONAL") == "OPEN"
    assert clean.status("PENDING CLOSE") == "CLOSING"


def test_sector_rejects_ordinary_which_is_a_type_not_a_sector():
    assert clean.sector("PUBLIC") == "PUBLIC"
    assert clean.sector("Independent/Private") == "INDEPENDENT"
    assert clean.sector("ORDINARY") == clean.UNKNOWN


def test_latitude_zero_is_not_a_school():
    # Latitude 0 is a point in the Atlantic Ocean, not South Africa.
    assert clean.coordinate("0") is None
    assert clean.coordinate("-33.9") == -33.9


def test_matric_cohort_excludes_primary():
    assert clean.has_matric_cohort("SECONDARY SCHOOL")
    assert clean.has_matric_cohort("Combined")
    assert not clean.has_matric_cohort("PRIMARY SCHOOL")
    assert not clean.has_matric_cohort("INTERMEDIATE SCHOOL")
