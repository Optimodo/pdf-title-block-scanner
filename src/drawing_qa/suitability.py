"""Whitelist check for purpose-of-issue / suitability / status values."""

from __future__ import annotations

import re

from drawing_qa.tokens import suitability_code

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


def suitability_whitelist_note(value: str) -> str:
    return f"Possible suitability / purpose-of-issue typo: {value!r} is not in the whitelist"
