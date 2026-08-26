"""Whitelist check for purpose-of-issue / suitability / status values."""

from __future__ import annotations

import re

from drawing_qa.tokens import revision_series, suitability_code

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")
_FILLER_WORDS = frozenset({"FOR", "SUITABLE", "THE"})

# Used when suitability.yaml has no purpose: block, and by tests.
DEFAULT_PURPOSE_REVIEW = ("S3",)
DEFAULT_PURPOSE_CONSTRUCTION = (
    "A - Construction",
    "A - For Construction",
    "S4 - Construction",
    "S4 - For Construction",
    "S5 - Construction",
    "S5 - For Construction",
)


def normalize_suitability(value: str) -> str:
    """Case-fold, treat '&' as AND, and collapse punctuation to spaces."""
    text = value.upper().replace("&", " AND ")
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


def suitability_tokens(value: str) -> frozenset[str]:
    """Normalised words with filler (for / suitable / the) removed."""
    tokens = []
    for token in normalize_suitability(value).split():
        if not token or token in _FILLER_WORDS:
            continue
        if token == "COMMENTS":
            token = "COMMENT"
        elif token == "APPROVALS":
            token = "APPROVAL"
        tokens.append(token)
    return frozenset(tokens)


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
    value_tokens = suitability_tokens(value)
    if value_tokens and any(value_tokens == suitability_tokens(item) for item in allowed):
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


def allowed_values_for_project(
    project: str | None,
    cfg_values: list[str],
    projects: dict[str, list[str]] | None,
    suggested: list[str] | None = None,
) -> list[str]:
    """Project list if present, else the default dropdown, else cfg_values."""
    if project and projects:
        listed = projects.get(project.strip().upper())
        if listed:
            return listed
    if suggested:
        return suggested
    return cfg_values


def project_has_purpose_list(project: str | None, projects: dict[str, list[str]] | None) -> bool:
    """True when this ISO project code has its own purpose-of-issue list."""
    if not project or not projects:
        return False
    return bool(projects.get(project.strip().upper()))


def _matches_purpose_list(value: str, entries: list[str] | tuple[str, ...]) -> bool:
    if not value.strip() or not entries:
        return False
    normalised = normalize_suitability(value)
    allowed_norm = [normalize_suitability(item) for item in entries if item and str(item).strip()]
    if normalised in allowed_norm:
        return True
    code = suitability_code(value)
    if not code:
        return False
    # A code listed alone (e.g. S3) classifies every status with that code.
    return code in allowed_norm


def suitability_purpose_family(
    value: str | None,
    *,
    review: list[str] | tuple[str, ...] | None = None,
    construction: list[str] | tuple[str, ...] | None = None,
) -> str | None:
    """Classify a status as review, construction, or neither from config lists."""
    if not value or not str(value).strip():
        return None
    review_entries = review if review is not None else DEFAULT_PURPOSE_REVIEW
    construction_entries = (
        construction if construction is not None else DEFAULT_PURPOSE_CONSTRUCTION
    )
    if _matches_purpose_list(value, construction_entries):
        return "construction"
    if _matches_purpose_list(value, review_entries):
        return "review"
    return None


def revision_purpose_mismatch_note(
    revision: str | None,
    suitability: str | None,
    *,
    review: list[str] | tuple[str, ...] | None = None,
    construction: list[str] | tuple[str, ...] | None = None,
) -> str | None:
    """P revisions belong with review/comment; C revisions with construction."""
    series = revision_series(revision)
    family = suitability_purpose_family(
        suitability, review=review, construction=construction
    )
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
