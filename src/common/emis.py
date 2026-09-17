"""EMIS number handling.

The EMIS number is the only key joining schools across every source, and it is
published inconsistently: with a leading zero in some files, without it in
others, and occasionally with stray whitespace. Everything must normalise it
the same way or joins silently under-match.
"""
import re


def normalise(value):
    """Strip to bare digits with no leading zeros. '0100000217' -> '100000217'."""
    return re.sub(r"\D", "", str(value or "")).lstrip("0")


def looks_like_emis(values):
    """True if these values are mostly EMIS numbers.

    Used to recover a column whose header is wrong - Gauteng's 2023 file ships
    its key column headed "G", truncated upstream.
    """
    hits = [v for v in values if re.fullmatch(r"0?\d{8,10}", str(v or "").strip())]
    return len(hits) >= max(3, len(values) // 2)
