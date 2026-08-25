"""Whitelist check for purpose-of-issue / suitability / status values."""

from __future__ import annotations

import re

from drawing_qa.tokens import revision_series, suitability_code

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def normalize_suitability(value: str) -> str:
    """Case-fold, treat '&' as AND, and collapse punctuation to spaces."""
    text = value.upper().replace("&", " AND ")
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


def suitability_is_allowed(
    value: str,
    allowed: list[str],
    *,
    accept_code_only: bool = True,
) -> bool:
    """Return True if value matches a whitelist entry (after normalisation)."""
    if not value.strip() or not allowed:
        return True
    normalised = normalize_suitability(value)
    allowed_norm = [normalize_suitability(item) for item in allowed if item and str(item).strip()]
    if normalised in allowed_norm:
        return True
    if not accept_code_only:
        return False
    code = suitability_code(value)
    if not code:
        return False
    if normalised != normalize_suitability(code):
        return False
    return any(
        item == code or item.startswith(code + " ")
        for item in allowed_norm
    )


def suitability_purpose_family(value: str | None) -> str | None:
    """Classify a status as review, construction, or neither.

    Review covers S3 and 'review and comment' wording. Construction covers
    descriptions that say construction (S4/S5/A construction, for construction).
    """
    if not value or not str(value).strip():
        return None
    text = normalize_suitability(value)
    code = suitability_code(value)
    is_construction = "CONSTRUCTION" in text
    is_review = code == "S3" or ("REVIEW" in text and "COMMENT" in text)
    if is_construction:
        return "construction"
    if is_review:
        return "review"
    return None


def revision_purpose_mismatch_note(revision: str | None, suitability: str | None) -> str | None:
    """P revisions belong with review/comment; C revisions with construction."""
    series = revision_series(revision)
    family = suitability_purpose_family(suitability)
    if series is None or family is None:
        return None
    if series == "P" and family == "construction":
        return (
            f"Revision {revision} is preliminary (P) but suitability is "
            f"{suitability!r}. P revisions should be S3 review and comment."
        )
    if series == "C" and family == "review":
        return (
            f"Revision {revision} is construction (C) but suitability is "
            f"{suitability!r}. C revisions should be a construction purpose of issue."
        )
    return None


def suitability_whitelist_note(value: str) -> str:
    return f"Possible suitability / purpose-of-issue typo: {value!r} is not in the whitelist"
