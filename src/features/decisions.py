"""The cleaning decisions, stored as data rather than buried in code.

Some cleaning is not a judgement call. "Q3" and "3" are the same funding tier
and merging them is simply correct - that lives in clean.py as a rule.

Other choices are genuine judgement, where a reasonable person could decide
either way and the answer changes the results:

  - Do special-needs schools belong in a study of matric attrition?
  - Is a school whose quintile reads "TO BE UPDATED" usable, or dropped?
  - Is DEEP RURAL its own context or just RURAL?

Those belong here, written to a file, version controlled, and read identically
by the app and the pipeline. The point is that the answer is recorded and can
be defended, not that any particular answer is right.
"""
import json
import os

from src.common.paths import ROOT

CONFIG = os.path.join(ROOT, "config", "cleaning_decisions.json")

DEFAULTS = {
    "include_phases": ["SECONDARY", "COMBINED"],
    "include_special_needs": False,
    "drop_unknown_quintile": False,
    "deep_rural_separate": True,
    "min_learners": 20,
    "drop_closing_schools": False,
    "require_educator_count": False,
}

EXPLANATIONS = {
    "include_phases": (
        "Which school phases enter the model. A primary school has no Grade 10, "
        "so it cannot contribute an observation about matric attrition."
    ),
    "include_special_needs": (
        "Special-needs schools and schools of skills do write matric, but their "
        "attrition works differently. Including them adds data; excluding them "
        "keeps the population consistent. Either is defensible if stated."
    ),
    "drop_unknown_quintile": (
        "Roughly 40,000 rows have no usable quintile. Dropping them loses "
        "schools that may differ systematically from schools with complete "
        "records, which would bias the model. Keeping them as an UNKNOWN level "
        "lets the model decide whether that absence carries signal."
    ),
    "deep_rural_separate": (
        "Only 24 rows are DEEP RURAL — too few to model alone, but not the same "
        "as RURAL. Merging them silently loses a distinction the source made "
        "deliberately."
    ),
    "min_learners": (
        "Very small schools produce unstable ratios: one learner leaving a "
        "school of 12 is an 8% swing. A floor stops that noise dominating."
    ),
    "drop_closing_schools": (
        "A school marked closing will lose its learners for reasons that have "
        "nothing to do with dropout risk. Keeping them teaches the model that "
        "closure looks like attrition."
    ),
    "require_educator_count": (
        "The learner:educator ratio needs both numbers. 6% of rows have no "
        "educator count. Requiring it costs those rows; allowing it means the "
        "ratio is missing for them."
    ),
}


def load():
    """Current decisions, falling back to defaults for anything unset."""
    values = dict(DEFAULTS)
    if os.path.exists(CONFIG):
        try:
            with open(CONFIG, encoding="utf-8") as handle:
                values.update(json.load(handle))
        except (json.JSONDecodeError, OSError):
            pass                      # a corrupt config should not stop the pipeline
    return values


def save(values):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    merged = dict(DEFAULTS)
    merged.update(values)
    with open(CONFIG, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=2, sort_keys=True)
    return merged


def changed_from_default(values=None):
    """Which decisions differ from the defaults, for the audit trail."""
    values = values or load()
    return {k: {"chosen": v, "default": DEFAULTS[k]}
            for k, v in values.items()
            if k in DEFAULTS and v != DEFAULTS[k]}
