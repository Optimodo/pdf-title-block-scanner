"""ISO level code (4th field) must be on the project's whitelist when one exists."""

from __future__ import annotations

import re

from drawing_qa.filename import parse_filename
from drawing_qa.models import DocumentResult


def iso_level_from_doc_ref(doc_ref: str | None) -> str | None:
    """Return the 4th hyphenated field (level), e.g. B1 in R456-MBS-BI-B1-DR-W-605-001."""
    if not doc_ref or not str(doc_ref).strip():
        return None
    parsed = parse_filename(str(doc_ref).strip())
    code = (parsed.parts.get("level") or "").strip().upper()
    if code:
        return code
    parts = re.split(r"[-_]+", str(doc_ref).strip().upper())
    if len(parts) >= 4:
        return parts[3] or None
    return None


def level_from_result(result: DocumentResult) -> str | None:
    """Prefer the title-block number; fall back to the filename."""
    return iso_level_from_doc_ref(
        result.titleblock.document_reference
    ) or iso_level_from_doc_ref(result.filename.document_reference)


def project_code_from_result(result: DocumentResult) -> str | None:
    code = (result.filename.parts.get("project") or "").strip().upper()
    if code:
        return code
    parsed = parse_filename(result.titleblock.document_reference or "")
    code = (parsed.parts.get("project") or "").strip().upper()
    return code or None


def allowed_levels_for_project(
    project: str | None, projects: dict[str, list[str]] | None
) -> list[str]:
    if not project or not projects:
        return []
    return [
        str(item).strip().upper()
        for item in projects.get(project.strip().upper(), [])
        if str(item).strip()
    ]


def level_is_allowed(got: str | None, allowed: list[str]) -> bool:
    if not allowed:
        return True
    if not got or not str(got).strip():
        return False
    return str(got).strip().upper() in {item.upper() for item in allowed}


def level_hint(
    got: str | None,
    project: str | None,
    hints: dict[str, dict[str, str]] | None,
) -> str:
    if not got or not project or not hints:
        return ""
    extra = hints.get(project.strip().upper()) or {}
    return str(extra.get(got.strip().upper()) or "").strip()


def level_whitelist_note(
    got: str | None,
    *,
    project_name: str = "",
    hint: str = "",
) -> str:
    label = project_name or "this project"
    shown = (got or "").strip() or "(blank)"
    text = (
        f"Level code {shown} is not on the {label} list "
        "(4th part of the drawing number)."
    )
    if hint:
        extra = hint.rstrip(".")
        text = f"{text} {extra}."
    return text
