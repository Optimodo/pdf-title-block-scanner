"""Whitelist check for the title-block client name."""

from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def normalize_client(value: str) -> str:
    """Case-fold, treat '&' as AND, and collapse punctuation to spaces."""
    text = value.upper().replace("&", " AND ")
    text = _NON_ALNUM.sub(" ", text)
    return " ".join(text.split())


def client_is_allowed(value: str | None, allowed: list[str]) -> bool:
    """True when the extracted client contains an allowed name as whole words."""
    if not value or not str(value).strip() or not allowed:
        return False
    haystack = f" {normalize_client(value)} "
    for item in allowed:
        needle = normalize_client(str(item))
        if needle and f" {needle} " in haystack:
            return True
    return False


def allowed_clients_for_project(
    project: str | None,
    projects: dict[str, list[str]] | None,
) -> list[str]:
    """Return the configured client names for this ISO project code, if any."""
    if not project or not projects:
        return []
    return list(projects.get(project.strip().upper()) or [])


def format_allowed_clients(allowed: list[str]) -> str:
    if not allowed:
        return ""
    if len(allowed) == 1:
        return allowed[0]
    if len(allowed) == 2:
        return f"{allowed[0]} or {allowed[1]}"
    return ", ".join(allowed[:-1]) + f", or {allowed[-1]}"


def client_whitelist_note(value: str | None, allowed: list[str]) -> str:
    expected = format_allowed_clients(allowed)
    if not value or not str(value).strip():
        return f"Client name is missing from the title block. Expected {expected}."
    return (
        f"Client name {value!r} is not valid for this project. Expected {expected}."
    )
