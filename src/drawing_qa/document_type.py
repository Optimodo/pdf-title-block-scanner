"""Schematic titles must use the project's ISO document-type code (5th field)."""

from __future__ import annotations

import re

from drawing_qa.filename import parse_filename
from drawing_qa.models import DocumentResult

_SCHEMATIC_WORD = re.compile(r"\bschematics?\b", re.IGNORECASE)


def title_looks_like_schematic(title: str | None) -> bool:
    if not title or not str(title).strip():
        return False
    return bool(_SCHEMATIC_WORD.search(str(title)))


def iso_type_from_doc_ref(doc_ref: str | None) -> str | None:
    """Return the 5th hyphenated field (type), e.g. DR in J106309-MBS-ZZ-ZZ-DR-X-620301."""
    if not doc_ref or not str(doc_ref).strip():
        return None
    parsed = parse_filename(str(doc_ref).strip())
    code = (parsed.parts.get("type") or "").strip().upper()
    if code:
        return code
    parts = re.split(r"[-_]+", str(doc_ref).strip().upper())
    if len(parts) >= 5:
        return parts[4] or None
    return None


def document_type_from_result(result: DocumentResult) -> str | None:
    """Prefer the title-block number; fall back to the filename."""
    return iso_type_from_doc_ref(
        result.titleblock.document_reference
    ) or iso_type_from_doc_ref(result.filename.document_reference)


def drawing_title_from_result(result: DocumentResult) -> str | None:
    return result.titleblock.title or result.filename.title


def schematic_type_for_project(
    project: str | None, schematic_types: dict[str, str] | None
) -> str | None:
    if not project or not schematic_types:
        return None
    code = schematic_types.get(project.strip().upper())
    if not code:
        return None
    return str(code).strip().upper() or None


def schematic_type_note(got: str, expected: str) -> str:
    return (
        f"Title contains schematic, so the document type (5th part of the drawing number) "
        f"should be {expected}, not {got}."
    )
