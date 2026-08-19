from __future__ import annotations

from pathlib import Path

from drawing_qa.docref import parse_name_without_ext
from drawing_qa.models import FilenameFields

ISO_FIELD_NAMES = (
    "project",
    "originator",
    "volume",
    "level",
    "type",
    "role",
    "number",
)


def _stem(path_or_name: str | Path) -> str:
    name = Path(path_or_name).name
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name.strip()


def parse_filename(
    path_or_name: str | Path,
    *,
    field_count: int = 7,
    revision_pattern: str = r"(?:[PC]\d{2}|[A-Z]\d?)",
) -> FilenameFields:
    """Parse a drawing filename into document reference, revision, and title.

    Uses the mbs-file-tools seven-block document-reference rules. ``field_count``
    and ``revision_pattern`` are accepted for compatibility; parsing follows
    the shared MBS rules rather than a simple hyphen split.
    """
    del field_count, revision_pattern
    stem = _stem(path_or_name)
    result = FilenameFields(raw_stem=stem)
    parsed = parse_name_without_ext(stem)
    result.notes.extend(parsed.warnings)

    revision = parsed.revision_pc or (parsed.other_revisions[0] if parsed.other_revisions else None)
    result.revision = revision.upper() if revision else None
    result.title = parsed.title

    if not parsed.doc_ref:
        return result

    doc_ref = parsed.doc_ref.upper()
    result.document_reference = doc_ref
    result.parse_ok = True
    parts = doc_ref.split("-")
    # Compound document numbers occupy extra dash segments; keep the first six
    # named fields and join the remainder as the number.
    if len(parts) >= 7:
        named = parts[:6]
        result.parts = dict(zip(ISO_FIELD_NAMES[:6], named, strict=False))
        result.parts["number"] = "-".join(parts[6:])
    return result
