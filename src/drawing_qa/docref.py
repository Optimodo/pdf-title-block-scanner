"""Filename document-reference parsing aligned with mbs-file-tools.

Rules follow https://github.com/Optimodo/mbs-file-tools (docref_core.py):
strip Explorer copy suffixes, take a trailing revision, match a 7- or 8-block
prefix (six segments + numeric document number, optionally compound), handle
YYMMDD export tails, then parse title / revision from the remainder.

Underscore and `` - `` are structural separators around the document reference,
title, and revision. Dashes *inside* the title (including ``Level 03-13`` and
``Block I - SVP&RWP ...``) stay part of the title.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REVISION_PC = re.compile(r"^[PC]\d{1,2}$", re.IGNORECASE)
REVISION_OTHER = re.compile(r"^[A-Z]\d{1,2}$", re.IGNORECASE)
# Six prefix blocks + document number. '-' or '_' may separate blocks; neither
# belongs inside a block. The remainder (title/revision) is not converted.
_CORE_DOC_REF = re.compile(r"^((?:[^_-]+[-_]){6}\d+)(.*)$")
_ORIGINATOR_TOKEN = re.compile(r"^[A-Za-z]{2,}$")
_LEADING_STRUCTURAL_SEP = re.compile(r"^(?:_|\s*-\s+|\s+|-(?=[A-Za-z0-9]))")
_TRAILING_REVISION = re.compile(
    r"(?:_|\s+-\s+|\s+|-)([A-Z]\d{1,2})\s*$",
    re.IGNORECASE,
)
_ONLY_REV = re.compile(r"^([PC]\d{1,2}|[A-Z]\d{2})$", re.IGNORECASE)
_MID_REV_THEN_TITLE = re.compile(
    r"^([PC]\d{1,2}|[A-Z]\d{2})(?:_|\s+-\s+|\s+|-)(.+)$",
    re.IGNORECASE,
)
# Rare non-standard sheet suffix on the last number: 51333.1 (DWGs often use 51333-1).
_DOTTED_SHEET_SUFFIX = re.compile(r"^\.(\d+)(.*)$")
_CANONICAL_DOTTED_SHEET = re.compile(r"(\d+)\.(\d+)$")


@dataclass
class ParseResult:
    doc_ref: str | None
    revision_pc: str | None
    other_revisions: list[str] = field(default_factory=list)
    title: str | None = None
    warnings: list[str] = field(default_factory=list)


def normalize_stem(name_without_ext: str) -> str:
    return name_without_ext.replace("_", "-").strip()


def strip_windows_duplicate_suffix(stem: str) -> tuple[str, list[str]]:
    removed: list[str] = []
    s = stem.rstrip()
    while True:
        prev = s
        match = re.search(r"\s*-\s*copy(?:\s*\(\d+\))?\s*$", s, re.IGNORECASE)
        if match:
            removed.append(s[match.start() :].strip())
            s = s[: match.start()].rstrip()
            continue
        match = re.search(r"\s+\(\d+\)\s*$", s)
        if match:
            removed.append(s[match.start() :].strip())
            s = s[: match.start()].rstrip()
            continue
        match = re.search(r"\(\d+\)\s*$", s)
        if match:
            removed.append(s[match.start() :].strip())
            s = s[: match.start()].rstrip()
            continue
        if s == prev:
            break
    return s, removed


def _norm_rev_token(raw: str) -> str:
    return raw[0].upper() + raw[1:]


def _clean_title(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip().lstrip("-_").strip()
    return text or None


def _strip_leading_structural_sep(tail: str) -> str:
    text = tail.strip()
    while text:
        match = _LEADING_STRUCTURAL_SEP.match(text)
        if not match:
            break
        text = text[match.end() :].strip()
    return text


def _strip_trailing_revision_suffix(s: str) -> tuple[str, str | None, list[str]]:
    rest = s.rstrip()
    match = _TRAILING_REVISION.search(rest)
    if not match:
        return rest, None, []
    tok = _norm_rev_token(match.group(1))
    if not REVISION_OTHER.match(tok):
        return rest, None, []
    rest = rest[: match.start()].rstrip()
    if REVISION_PC.match(tok):
        return rest, tok[0].upper() + tok[1:], []
    return rest, None, [tok[0].upper() + tok[1:]]


def _parse_tail_after_docref(tail: str) -> tuple[str | None, list[str], str | None]:
    """Parse title / mid-revision after the document reference.

    Leading ``_``, `` - ``, or a glued ``-`` is a separator. Any later dashes,
    including `` - `` inside the title, are kept.
    """
    mid_pc: str | None = None
    mid_other: list[str] = []
    if not tail or not tail.strip():
        return None, [], None

    def set_mid(token: str) -> None:
        nonlocal mid_pc
        tok = _norm_rev_token(token)
        if REVISION_PC.match(tok):
            mid_pc = tok[0].upper() + tok[1:]
        else:
            mid_other.append(tok[0].upper() + tok[1:])

    text = _strip_leading_structural_sep(tail)
    if not text:
        return None, [], None

    only_rev = _ONLY_REV.fullmatch(text)
    if only_rev:
        set_mid(only_rev.group(1))
        return mid_pc, mid_other, None

    match = _MID_REV_THEN_TITLE.match(text)
    if match:
        set_mid(match.group(1))
        return mid_pc, mid_other, _clean_title(match.group(2))

    return None, [], _clean_title(text)


def _pop_trailing_revisions(parts: list[str]) -> tuple[list[str], str | None, list[str]]:
    pc_rev: str | None = None
    other: list[str] = []
    while parts and REVISION_OTHER.match(parts[-1]):
        tok = parts.pop()
        if REVISION_PC.match(tok):
            if pc_rev is not None:
                other.insert(0, pc_rev)
            pc_rev = tok[0].upper() + tok[1:]
        else:
            other.insert(0, tok)
    return parts, pc_rev, other


def _is_yymmdd(value: str) -> bool:
    if not re.fullmatch(r"\d{6}", value):
        return False
    month, day = int(value[2:4]), int(value[4:6])
    return 1 <= month <= 12 and 1 <= day <= 31


def _strip_date_originator_from_tail(tail: str) -> tuple[str, str | None]:
    match = re.match(r"^[-_](\d{6})(?:[-_]([A-Za-z]{2,}))?(.*)$", tail)
    if not match or not _is_yymmdd(match.group(1)):
        return tail, None
    date, org, rest = match.group(1), match.group(2), match.group(3)
    if org is not None and not _ORIGINATOR_TOKEN.match(org):
        return tail, None
    removed = f"{date}-{org}" if org else date
    return rest, removed


def _extend_compound_or_strip_date_suffix(base: str, tail: str) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    match = re.match(r"^[-_](\d+)(.*)$", tail)
    if match:
        second, rest = match.group(1), match.group(2)
        if _is_yymmdd(second):
            org_m = re.match(r"^[-_]([A-Za-z]{2,})(.*)$", rest)
            if org_m and _ORIGINATOR_TOKEN.match(org_m.group(1)):
                removed = f"{second}-{org_m.group(1)}"
                rest = org_m.group(2)
            else:
                removed = second
            notes.append(f"removed date/originator export suffix {removed!r}")
            return base.replace("_", "-"), rest, notes
        base = f"{base.replace('_', '-')}-{second}"
        tail = rest

    tail, removed = _strip_date_originator_from_tail(tail)
    if removed is not None:
        notes.append(f"removed date/originator export suffix {removed!r}")
    return base.replace("_", "-"), tail, notes


def canonical_doc_ref(value: str | None) -> str | None:
    """Uppercase ISO ref; treat 51333.1 and 51333-1 as the same sheet suffix."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", "", value).strip().upper().replace("_", "-")
    if not cleaned:
        return None
    return _CANONICAL_DOTTED_SHEET.sub(r"\1-\2", cleaned)


def sheet_suffix_style(doc_ref: str | None) -> str | None:
    """How a rare extra sheet number is written: 'dot' (51333.1) or 'hyphen' (51333-1)."""
    if not doc_ref:
        return None
    parts = [part for part in doc_ref.replace("_", "-").split("-") if part]
    if not parts:
        return None
    last = parts[-1]
    if re.fullmatch(r"\d+\.\d+", last):
        return "dot"
    if (
        len(parts) >= 8
        and last.isdigit()
        and parts[-2].isdigit()
        and 1 <= len(last) <= 2
        and len(parts[-2]) >= 4
    ):
        return "hyphen"
    return None


def _title_is_date_originator_only(title: str | None) -> bool:
    if not title:
        return False
    match = re.fullmatch(r"(\d{6})(?:[-\s]+([A-Za-z]{2,}))?", title.strip())
    if not match or not _is_yymmdd(match.group(1)):
        return False
    org = match.group(2)
    return org is None or bool(_ORIGINATOR_TOKEN.match(org))


def _strip_spurious_docnum_segment(parts: list[str]) -> tuple[list[str], str | None]:
    if len(parts) < 8:
        return parts, None
    if not (parts[-1].isdigit() and parts[-2].isdigit()):
        return parts, None
    if len(parts) - 2 < 6:
        return parts, None
    short, main = parts[-2], parts[-1]
    if len(short) < len(main):
        return parts[:-2] + [main], short
    return parts, None


def _extract_body_and_docnum(parts: list[str]) -> tuple[list[str], str] | None:
    if not parts:
        return None
    if parts[-1].isdigit():
        if len(parts) >= 2 and parts[-2].isdigit():
            doc_num = f"{parts[-2]}-{parts[-1]}"
            body = parts[:-2]
        else:
            doc_num = parts[-1]
            body = parts[:-1]
    else:
        return None
    if len(body) != 6:
        return None
    return body, doc_num


def parse_name_without_ext(name_without_ext: str) -> ParseResult:
    warnings: list[str] = []
    stem = name_without_ext.strip()
    stem, copy_tails = strip_windows_duplicate_suffix(stem)
    if copy_tails:
        warnings.append(
            "removed Windows duplicate filename suffix(es): "
            + "; ".join(repr(item) for item in copy_tails)
        )

    stem, trail_pc, trail_other = _strip_trailing_revision_suffix(stem)
    match = _CORE_DOC_REF.match(stem)
    if not match:
        warnings.append(
            "could not parse 7-block document reference "
            "(need 6 prefix blocks + numeric document number)"
        )
        return ParseResult(
            doc_ref=None,
            revision_pc=trail_pc,
            other_revisions=trail_other,
            title=None,
            warnings=warnings,
        )

    base = match.group(1).strip()
    tail = match.group(2).rstrip()
    base, tail, date_notes = _extend_compound_or_strip_date_suffix(base, tail)
    warnings.extend(date_notes)

    sheet_suffix = None
    dotted = _DOTTED_SHEET_SUFFIX.match(tail)
    if dotted:
        sheet_suffix = dotted.group(1)
        tail = dotted.group(2)

    mid_pc, mid_other, title = _parse_tail_after_docref(tail)
    if _title_is_date_originator_only(title):
        warnings.append(f"removed date/originator export suffix {title!r}")
        title = None

    revision_pc = trail_pc if trail_pc else mid_pc
    if trail_pc and mid_pc and trail_pc != mid_pc:
        warnings.append(
            f"conflicting P/C revisions after doc ref ({mid_pc}) vs after title "
            f"({trail_pc}); using {revision_pc}"
        )
    other_rev = list(trail_other)
    other_rev.extend(mid_other)

    parts = [part for part in base.split("-") if part]
    parts, pop_pc, pop_other = _pop_trailing_revisions(parts)
    if pop_pc:
        revision_pc = revision_pc or pop_pc
    if pop_other:
        other_rev.extend(pop_other)

    parts, spurious = _strip_spurious_docnum_segment(parts)
    if spurious is not None:
        warnings.append(
            f"removed spurious numeric segment {spurious!r} "
            "between specialisation and document number"
        )

    extracted = _extract_body_and_docnum(parts)
    if extracted is None:
        warnings.append(
            "could not parse 7-block document reference "
            "(need 6 prefix blocks + numeric document number)"
        )
        return ParseResult(
            doc_ref=None,
            revision_pc=revision_pc,
            other_revisions=other_rev,
            title=title,
            warnings=warnings,
        )

    body, doc_num = extracted
    if sheet_suffix:
        doc_num = f"{doc_num}.{sheet_suffix}"
    return ParseResult(
        doc_ref="-".join(body + [doc_num]),
        revision_pc=revision_pc,
        other_revisions=other_rev,
        title=title,
        warnings=warnings,
    )
