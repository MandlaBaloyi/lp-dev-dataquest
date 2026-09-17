"""Normalisation rules for the raw school panel.

Every rule here is a judgement call made explicit. The source data publishes
the same fact many ways - school phase appears in 22 spellings, quintile in 18,
the no-fee flag in 12 - and a model reads each spelling as a separate category
unless something maps them together.

These rules are the single source of truth. The Streamlit app reads them, the
pipeline reads them, the tests read them. Nothing re-implements them, because
the moment the app cleans differently from the pipeline, the numbers on screen
stop describing the model that was actually trained.

UNKNOWN is deliberately preserved rather than dropped. "TO BE UPDATED" appears
on 39,923 rows of the training population; discarding those rows would discard
schools that may differ systematically from schools whose records are complete.
Keeping unknown as its own level lets the model decide whether it carries
signal instead of us assuming it does not.
"""
import re

UNKNOWN = "UNKNOWN"

# Values that mean "no value recorded", whatever column they appear in.
NULL_MARKERS = {
    "", ".", "NULL", "NONE", "N/A", "NA", "UNKNOWN", "UNKNOWN ENTRY",
    "TO BE UPDATED", "NOT APPLICABLE", "NO RESPONSE", "99",
}

# Phases that can hold a Grade 10-12 cohort. A primary school cannot contribute
# a single observation to a question about matric, so it is not in scope.
MATRIC_PHASES = {"SECONDARY", "COMBINED"}


def _base(value):
    """Upper-case, collapse whitespace, and resolve null markers to UNKNOWN."""
    text = re.sub(r"\s+", " ", str(value or "").strip()).upper()
    return UNKNOWN if text in NULL_MARKERS else text


def phase(value):
    """'Secondary School', 'SECONDARY', 'Secondary' -> SECONDARY."""
    text = _base(value)
    if text == UNKNOWN:
        return UNKNOWN
    for known in ("PRE-PRIMARY", "INTERMEDIATE", "SECONDARY", "COMBINED",
                  "PRIMARY", "SPECIAL", "SKILLS", "HOSPITAL", "ECD"):
        if known in text:
            return known
    return UNKNOWN


def quintile(value):
    """'3', 'Q3' and 'NQ3' are the same funding tier. Returns '1'-'5' or UNKNOWN.

    Quintile is South Africa's school funding band: 1 is the poorest and
    no-fee, 5 the wealthiest. It is the strongest single predictor available.
    """
    text = _base(value)
    match = re.search(r"[1-5]", text)
    return match.group(0) if match else UNKNOWN


def nofee(value):
    """Collapse 12 spellings into NO_FEE / FEE_CHARGING / UNKNOWN.

    'Free Charging' is a typo for 'Fee Charging' at source and is read as
    fee-charging, matching the 'NO' it appears alongside.
    """
    text = _base(value)
    if text == UNKNOWN:
        return UNKNOWN
    if text in {"YES", "Y", "NO FEE", "NOFEE", "NO-FEE"}:
        return "NO_FEE"
    if text in {"NO", "N", "FEE CHARGING", "FEE PAYING", "FREE CHARGING"}:
        return "FEE_CHARGING"
    return UNKNOWN


def urbanrural(value):
    """Collapse 13 spellings. DEEP RURAL is kept apart from RURAL.

    Only 24 rows are DEEP RURAL, too few to model on their own, but they are
    not the same thing as RURAL and merging them silently would lose that.
    Callers that need a binary split can fold it in themselves.
    """
    text = _base(value)
    if text == UNKNOWN:
        return UNKNOWN
    if "DEEP" in text:
        return "DEEP_RURAL"
    if "PERI" in text:
        return "PERI_URBAN"
    if "URBAN" in text:
        return "URBAN"
    if "RURAL" in text:
        return "RURAL"
    return UNKNOWN


def status(value):
    """OPEN / Open / OPERATIONAL all mean open. Everything else is closing."""
    text = _base(value)
    if text == UNKNOWN:
        return UNKNOWN
    if text in {"OPEN", "OPERATIONAL"}:
        return "OPEN"
    return "CLOSING"


def sector(value):
    """PUBLIC or INDEPENDENT. 'ORDINARY' is a school type, not a sector."""
    text = _base(value)
    if "INDEPENDENT" in text or "PRIVATE" in text:
        return "INDEPENDENT"
    if "PUBLIC" in text:
        return "PUBLIC"
    return UNKNOWN


def coordinate(value):
    """Latitude/longitude, or None where the value cannot be a South African school.

    881 rows carry latitude 0, which is a point in the Atlantic Ocean off the
    west African coast. Left in place, a map plots schools at sea and any
    distance feature built from them is wrong.
    """
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if number == 0:
        return None
    return number


def count(value):
    """Learner and educator counts arrive as text, sometimes as junk markers."""
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return int(number) if number > 0 else None


def has_matric_cohort(phase_value):
    """True where the school can hold a Grade 10-12 cohort."""
    return phase(phase_value) in MATRIC_PHASES


CLEANERS = {
    "phase": phase,
    "quintile": quintile,
    "nofee": nofee,
    "urbanrural": urbanrural,
    "status": status,
    "sector": sector,
}


def clean_row(row):
    """Apply every rule to one panel row, returning a new dict."""
    out = dict(row)
    for column, cleaner in CLEANERS.items():
        if column in out:
            out[column] = cleaner(out[column])
    for column in ("lat", "lon"):
        if column in out:
            out[column] = coordinate(out[column])
    for column in ("learners", "educators"):
        if column in out:
            out[column] = count(out[column])
    return out
