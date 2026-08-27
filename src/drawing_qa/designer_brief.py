"""Plain-language actions for designers, derived from check issues."""

from __future__ import annotations

from drawing_qa.history import history_first_row
from drawing_qa.models import CheckStatus, DocumentResult, FieldComparison
from drawing_qa.suitability import suitability_is_allowed
from drawing_qa.tokens import next_revision, parse_pc_revision, revision_series


_FIELD_NOUN = {
    "document_reference": "drawing number",
    "title": "drawing title",
    "revision": "revision",
    "suitability": "purpose of issue",
    "date": "date",
}

_PURPOSE_STATUSES = frozenset(
    {
        CheckStatus.SUITABILITY_ERROR,
        CheckStatus.PURPOSE_MISMATCH,
        CheckStatus.PURPOSE_INCONSISTENT,
    }
)


def _quote(value: str | None) -> str:
    text = (value or "").strip()
    return f"'{text}'" if text else "(blank)"


def _comp(result: DocumentResult, name: str) -> FieldComparison | None:
    for item in result.comparisons:
        if item.name == name:
            return item
    return None


def _hcomp(result: DocumentResult, name: str) -> FieldComparison | None:
    for item in result.history_comparisons:
        if item.name == name:
            return item
    return None


_SEE_PURPOSE_LIST = "see bottom of this sheet for the approved list"
_APPROVED_LIST_REF = f"from the approved list ({_SEE_PURPOSE_LIST})"


def designer_purpose_groups(
    results: list[DocumentResult],
) -> list[tuple[str, list[str], bool]]:
    """Unique purpose lists for the Designer actions footer.

    Returns (heading, values, official). Named project lists are preferred;
    drawings without a project list use the default approved list.
    """
    ordered: list[tuple[str, ...]] = []
    meta: dict[tuple[str, ...], tuple[str, bool]] = {}
    for result in results:
        values = tuple(
            item
            for item in (result.designer_purpose_values or result.allowed_suitability)
            if item
        )
        if not values:
            continue
        project = (result.filename.parts.get("project") or "").strip().upper()
        official = result.purpose_list_official
        if official:
            name = result.purpose_list_name
            extra = f" ({name})" if name else ""
            label = f"Project {project}{extra}" if project else "Approved list"
        else:
            label = "Default approved list"
        if values not in meta:
            ordered.append(values)
            meta[values] = (label, official)
        elif official and not meta[values][1]:
            meta[values] = (label, official)
    return [(meta[values][0], list(values), meta[values][1]) for values in ordered]


def _mismatch_action(result: DocumentResult, *, skip_suitability: bool) -> list[str]:
    actions: list[str] = []
    for name, noun in _FIELD_NOUN.items():
        if skip_suitability and name == "suitability":
            continue
        item = _comp(result, name)
        if not item or item.matched is not False:
            continue
        fn, tb = item.filename_value, item.titleblock_value
        if name == "document_reference":
            filename = result.original_filename or result.path.name
            if fn:
                actions.append(
                    f"The file-name drawing number is {_quote(fn)} and the "
                    f"title-block drawing number is {_quote(tb)}. These should match, "
                    "so one of them needs changing."
                )
            else:
                actions.append(
                    f"File name is {_quote(filename)}. The title-block drawing number "
                    f"is {_quote(tb)} but the file name is not a valid ISO 19650 name. "
                    "These should match, so one of them needs changing."
                )
            continue
        if fn and tb:
            actions.append(
                f"Change the {noun} in the title block from {_quote(tb)} to {_quote(fn)} "
                "so it matches the file name."
            )
        elif fn:
            actions.append(
                f"Add {noun} {_quote(fn)} to the title block so it matches the file name."
            )
        else:
            actions.append(
                f"The title block {noun} is {_quote(tb)} but the file name has no {noun}. "
                "Make the file name and title block agree."
            )
    return actions


def _history_action(result: DocumentResult, *, skip_suitability: bool) -> list[str]:
    actions: list[str] = []
    tb = result.titleblock
    latest = tb.history.latest if tb.history else None
    first = history_first_row(tb.history) if tb.history else None
    rev = _hcomp(result, "history_revision")
    if rev and rev.matched is False:
        actions.append(
            f"The current revision is {_quote(tb.revision)} but the latest revision-history "
            f"row is {_quote(latest.revision if latest else None)}. Add a history row for "
            f"{_quote(tb.revision)}, or change the current revision to match the latest history row."
        )
    date = _hcomp(result, "history_date")
    if date and date.matched is False:
        actions.append(
            f"Change the title-block date so it matches the original issue date "
            f"({_quote(first.date if first else None)}) or the latest history date "
            f"({_quote(latest.date if latest else None)}). It currently shows {_quote(tb.date)}."
        )
    if skip_suitability:
        return actions
    if not _history_purpose_is_status(result):
        return actions
    suit = _hcomp(result, "history_suitability")
    if suit and suit.matched is False:
        actions.append(
            f"Change the purpose of issue so it matches the latest history row "
            f"({_quote(latest.suitability if latest else None)}). "
            f"It currently shows {_quote(tb.suitability)}."
        )
    return actions


def _history_purpose_is_status(result: DocumentResult) -> bool:
    """True when the latest history row looks like a purpose of issue, not a note."""
    latest = result.titleblock.history.latest if result.titleblock.history else None
    value = latest.suitability if latest else None
    if not value:
        hist = _hcomp(result, "history_suitability")
        value = hist.titleblock_value if hist else None
    if not value:
        return False
    allowed = result.allowed_suitability or result.designer_purpose_values
    if not allowed:
        return True
    return suitability_is_allowed(value, allowed)


def _purpose_action(result: DocumentResult, issues: list[CheckStatus]) -> str | None:
    """One combined purpose-of-issue instruction; points at the sheet list."""
    purpose_flags = [
        item for item in issues if item in _PURPOSE_STATUSES and item != CheckStatus.PURPOSE_INCONSISTENT
    ]
    hist = _hcomp(result, "history_suitability")
    hist_bad = (
        hist is not None
        and hist.matched is False
        and _history_purpose_is_status(result)
    )
    if not purpose_flags and not hist_bad:
        return None

    tb = result.titleblock
    parts = [f"Purpose of issue is currently {_quote(tb.suitability)}."]
    if CheckStatus.SUITABILITY_ERROR in purpose_flags:
        parts.append(f"It is not on the approved list ({_SEE_PURPOSE_LIST}).")
    if CheckStatus.PURPOSE_MISMATCH in purpose_flags:
        series = revision_series(tb.revision)
        rev = tb.revision or "This revision"
        if series == "P":
            parts.append(
                f"{rev} is a P (preliminary) revision, so use a review purpose "
                f"{_APPROVED_LIST_REF} rather than construction."
            )
        elif series == "C":
            parts.append(
                f"{rev} is a C (construction) revision, so use a construction purpose "
                f"{_APPROVED_LIST_REF} rather than review."
            )
        else:
            parts.append(
                "The revision and purpose of issue do not belong together. "
                f"Use a matching purpose {_APPROVED_LIST_REF}."
            )
    if hist_bad:
        latest = tb.history.latest if tb.history else None
        parts.append(
            f"The latest revision-history row shows "
            f"{_quote(latest.suitability if latest else None)}. "
            "The current purpose and that row must match."
        )
    return " ".join(parts)


def _issue_actions(
    result: DocumentResult,
    status: CheckStatus,
    *,
    skip_purpose: bool,
) -> list[str]:
    if status == CheckStatus.MISMATCH:
        return _mismatch_action(result, skip_suitability=skip_purpose)
    if status == CheckStatus.HISTORY_MISMATCH:
        return _history_action(result, skip_suitability=skip_purpose)
    if status == CheckStatus.SPELLING_ERROR:
        words = ", ".join(result.spelling_errors) or "see the title"
        return [f"Correct the spelling in the drawing title. Flagged word(s): {words}."]
    if status in _PURPOSE_STATUSES:
        return []
    if status == CheckStatus.DATE_REGRESSION:
        detail = next((n for n in result.notes if "Date regression" in n), "")
        if detail:
            return [detail.rstrip(".") + "."]
        return [
            "In the revision history, later revisions must have the same or a later date "
            "than earlier ones."
        ]
    if status == CheckStatus.DUPLICATE_REFERENCE:
        return [
            "This drawing number is used on more than one PDF. "
            "Give this sheet a unique drawing number."
        ]
    if status == CheckStatus.INCOMPLETE:
        return [
            "The drawing number in the title block could not be read. "
            "Check the NUMBER / DRAWING NO cell contains selectable text."
        ]
    if status == CheckStatus.UNDETECTED:
        return [
            "The title block could not be read. Check that NUMBER, TITLE, REVISION "
            "and SUITABILITY labels are printed clearly."
        ]
    if status == CheckStatus.FILENAME_PARSE_ERROR:
        return [
            "Rename the PDF to ISO 19650 format "
            "(Project-Originator-Volume-Level-Type-Role-Number)."
        ]
    if status == CheckStatus.DWG_ISSUE:
        if result.dwg_issue == "sheet_suffix":
            return [
                "The PDF and DWG use different sheet-number punctuation (.1 vs -1). "
                "Use the same form on both files."
            ]
        if result.dwg_issue == "name_differs" and result.paired_dwg:
            return [
                f"Rename the DWG ({result.paired_dwg.name}) so it matches the PDF file name."
            ]
        return ["Issue a DWG with the same drawing number as this PDF."]
    if status == CheckStatus.PORTAL_REVISION:
        if result.construction_upgrade_required:
            return [_construction_upgrade_action(result)]
        return [_portal_revision_action(result)]
    if status == CheckStatus.PORTAL_TITLE:
        return [_portal_title_action(result)]
    if status == CheckStatus.ERROR:
        return ["This PDF could not be opened. Re-export the drawing."]
    return []


def _current_revision(result: DocumentResult) -> str:
    return (result.titleblock.revision or result.filename.revision or "").strip()


def _construction_upgrade_action(result: DocumentResult) -> str:
    current = _quote(_current_revision(result))
    status = result.portal_status or "A or B"
    return (
        f"The portal list has this drawing at {_quote(result.portal_revision)} with status "
        f"{_quote(status)}. That P issue is approved, so this issue should be 'C01' "
        f"(first construction issue). The drawing currently shows {current}."
    )


def _portal_revision_action(result: DocumentResult) -> str:
    current = _quote(_current_revision(result))
    if result.portal_revision:
        nxt = next_revision(result.portal_revision) or "the next revision"
        extra = ""
        parsed = parse_pc_revision(result.portal_revision)
        if parsed and parsed[0] == "P":
            extra = " (or 'C01' if this is the first construction issue)"
        return (
            f"The portal list has this drawing at {_quote(result.portal_revision)}. "
            f"The drawing currently shows {current}. "
            f"This issue should be {_quote(nxt)}{extra}."
        )
    allowed = [item for item in result.portal_first_revisions if item] or ["P01"]
    if len(allowed) == 1:
        expected = allowed[0]
    elif len(allowed) == 2:
        expected = f"{allowed[0]} or {allowed[1]}"
    else:
        expected = ", ".join(allowed[:-1]) + f", or {allowed[-1]}"
    return (
        f"This drawing is not on the portal yet. The drawing currently shows {current}; "
        f"the first issue should be {expected}."
    )


def _portal_title_action(result: DocumentResult) -> str:
    local = (result.titleblock.title or result.filename.title or "").strip()
    return (
        f"The portal list title is {_quote(result.portal_title)} and the title-block title is "
        f"{_quote(local)}. These should match, so one of them needs changing."
    )


def designer_actions(result: DocumentResult) -> str:
    """One or more plain-language instructions for the designer."""
    issues = [item for item in result.issues if item != CheckStatus.MULTIPLE_ISSUES]
    if not issues and result.status not in (CheckStatus.MATCH, CheckStatus.MULTIPLE_ISSUES):
        issues = [result.status]
    purpose_line = _purpose_action(result, issues)
    skip_purpose = purpose_line is not None
    upgrade_needed = result.construction_upgrade_required and (
        CheckStatus.PORTAL_REVISION in issues
    )
    if upgrade_needed:
        skip_purpose = True
        purpose_line = None
    lines: list[str] = []
    seen: set[str] = set()
    if upgrade_needed:
        upgrade_line = _construction_upgrade_action(result)
        seen.add(upgrade_line)
        lines.append(upgrade_line)
    if purpose_line:
        seen.add(purpose_line)
        lines.append(purpose_line)
    for status in issues:
        if status in _PURPOSE_STATUSES:
            continue
        if upgrade_needed and status == CheckStatus.PORTAL_REVISION:
            continue
        for line in _issue_actions(result, status, skip_purpose=skip_purpose):
            if line not in seen:
                seen.add(line)
                lines.append(line)
    if not lines:
        return "No designer action required."
    if len(lines) == 1:
        return lines[0]
    return "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))


def designer_doc_ref(result: DocumentResult) -> str:
    return (
        result.titleblock.document_reference
        or result.filename.document_reference
        or ""
    )


def designer_title(result: DocumentResult) -> str:
    return result.titleblock.title or result.filename.title or ""
