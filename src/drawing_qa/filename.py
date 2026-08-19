from __future__ import annotations

import re
from pathlib import Path

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


def _parse_loose_suffix(
    stem: str,
    revision_pattern: str,
) -> tuple[str | None, str | None]:
    """Best-effort title/revision when the stem is not ISO 19650."""
    rev_re = re.compile(
        rf"(?:^|[\s_\-]+)(?P<rev>{revision_pattern})$",
        re.IGNORECASE,
    )
    rev_match = rev_re.search(stem)
    if not rev_match:
        return None, None
    revision = rev_match.group("rev").upper()
    title_part = stem[: rev_match.start()].strip(" _-")
    return revision, title_part or None


def parse_filename(
    path_or_name: str | Path,
    *,
    field_count: int = 7,
    revision_pattern: str = r"(?:[PC]\d{2}|[A-Z]\d?)",
) -> FilenameFields:
    """Parse an ISO 19650-style drawing filename.

    Expected core: Project-Originator-Volume-Level-Type-Role-Number
    Optional suffix: title and/or revision separated by space, underscore, or hyphen.

    When the stem is not ISO 19650, parsing continues with empty document reference
    but may still pick up a trailing revision and any preceding title text.
    """
    stem = _stem(path_or_name)
    result = FilenameFields(raw_stem=stem)
    if field_count < 2:
        result.notes.append("field_count must be at least 2")
        return result

    token_re = r"[A-Za-z0-9]+"
    core = rf"(?P<doc_ref>{token_re}(?:-{token_re}){{{field_count - 1}}})"
    match = re.match(rf"^{core}(?P<rest>.*)$", stem)
    if not match:
        result.notes.append(
            f"Filename does not start with {field_count} hyphen-separated ISO 19650 fields"
        )
        revision, title = _parse_loose_suffix(stem, revision_pattern)
        result.revision = revision
        result.title = title
        if revision:
            result.notes.append("Loose revision found in filename (non-ISO stem)")
        if title:
            result.notes.append("Loose title found in filename (non-ISO stem)")
        return result

    doc_ref = match.group("doc_ref")
    parts = dict(zip(ISO_FIELD_NAMES[:field_count], doc_ref.split("-"), strict=False))
    rest = match.group("rest") or ""
    rest = re.sub(r"^[\s_\-]+", "", rest)

    revision = None
    title = None
    rev_re = re.compile(
        rf"(?:^|[\s_\-]+)(?P<rev>{revision_pattern})$",
        re.IGNORECASE,
    )
    if rest:
        rev_match = rev_re.search(rest)
        if rev_match:
            revision = rev_match.group("rev")
            title_part = rest[: rev_match.start()].strip(" _-")
            title = title_part or None
        else:
            title = rest.strip(" _-") or None

    result.document_reference = doc_ref.upper()
    result.revision = revision.upper() if revision else None
    result.title = title
    result.parts = parts
    result.parse_ok = True
    if not revision:
        result.notes.append("No revision found in filename")
    if not title:
        result.notes.append("No title found in filename")
    return result
