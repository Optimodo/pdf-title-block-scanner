from __future__ import annotations

import re

from drawing_qa.models import (
    CheckStatus,
    Confidence,
    DocumentResult,
    FieldComparison,
    FilenameFields,
    TitleBlockFields,
)
from drawing_qa.tokens import dates_equal, suitability_code


def normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", "", value).strip().upper()
    cleaned = cleaned.replace("_", "-")
    return cleaned or None


def normalize_title(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"[\s_\-]+", " ", value).strip().upper()
    return cleaned or None


def _compare_code(left: str | None, right: str | None) -> tuple[bool | None, str]:
    a, b = normalize_code(left), normalize_code(right)
    if a is None and b is None:
        return None, "both empty"
    if a is None:
        return None, "missing on left"
    if b is None:
        return None, "missing on right"
    return a == b, "equal" if a == b else f"{a} != {b}"


def _compare_title(left: str | None, right: str | None) -> tuple[bool | None, str]:
    a, b = normalize_title(left), normalize_title(right)
    if a is None and b is None:
        return None, "both empty"
    if a is None:
        return None, "missing on left"
    if b is None:
        return None, "missing on right"
    return a == b, "equal" if a == b else f"{a} != {b}"


def _compare_suitability(left: str | None, right: str | None) -> tuple[bool | None, str]:
    a, b = suitability_code(left), suitability_code(right)
    if a is None and b is None:
        if left and right:
            return _compare_title(left, right)
        return None, "both empty"
    if a is None:
        return None, "missing on left"
    if b is None:
        return None, "missing on right"
    return a == b, "equal" if a == b else f"{a} != {b}"


def _compare_date(left: str | None, right: str | None) -> tuple[bool | None, str]:
    if not left and not right:
        return None, "both empty"
    if not left:
        return None, "missing on left"
    if not right:
        return None, "missing on right"
    matched = dates_equal(left, right)
    if matched is None:
        return None, "unparsed"
    return matched, "equal" if matched else f"{left} != {right}"


def _layout_undetected(titleblock: TitleBlockFields) -> bool:
    if not titleblock.layout_id:
        return True
    if titleblock.document_reference is None and titleblock.revision is None:
        return any("below threshold" in note for note in titleblock.notes)
    return False


def _history_copied(titleblock: TitleBlockFields, name: str) -> bool:
    field = titleblock.fields.get(name)
    return bool(field and field.source == "history")


def compare_history(titleblock: TitleBlockFields) -> tuple[list[FieldComparison], bool, list[str]]:
    comparisons: list[FieldComparison] = []
    notes: list[str] = []
    latest = titleblock.history.latest if titleblock.history else None
    if latest is None:
        return comparisons, False, notes

    def add(name: str, current: str | None, history_value: str | None, kind: str) -> None:
        if _history_copied(titleblock, name):
            comparisons.append(
                FieldComparison(
                    name=f"history_{name}",
                    filename_value=current,
                    titleblock_value=history_value,
                    matched=True,
                    detail="current field taken from latest history row",
                )
            )
            return
        if kind == "date":
            matched, detail = _compare_date(current, history_value)
        elif kind == "suitability":
            matched, detail = _compare_suitability(current, history_value)
        else:
            matched, detail = _compare_code(current, history_value)
        comparisons.append(
            FieldComparison(
                name=f"history_{name}",
                filename_value=current,
                titleblock_value=history_value,
                matched=matched,
                detail=detail,
            )
        )

    add("revision", titleblock.revision, latest.revision, "code")
    add("date", titleblock.date, latest.date, "date")
    add("suitability", titleblock.suitability, latest.suitability, "suitability")

    mismatched = False
    for item in comparisons:
        if item.name == "history_revision" and item.matched is False:
            mismatched = True
            notes.append(f"History latest revision {item.titleblock_value} != current {item.filename_value}")
        elif item.name == "history_date" and item.matched is False:
            mismatched = True
            notes.append(f"History latest date {item.titleblock_value} != current {item.filename_value}")
        elif item.name == "history_suitability" and item.matched is False:
            mismatched = True
            notes.append(
                f"History latest status {item.titleblock_value} != current {item.filename_value}"
            )
    return comparisons, mismatched, notes


def compare_document(
    filename: FilenameFields,
    titleblock: TitleBlockFields,
    rules: dict[str, str],
) -> tuple[list[FieldComparison], list[FieldComparison], CheckStatus, list[str]]:
    comparisons: list[FieldComparison] = []
    notes: list[str] = []

    def add(name: str, fn_val: str | None, tb_val: str | None, kind: str) -> None:
        if kind == "title":
            matched, detail = _compare_title(fn_val, tb_val)
        elif kind == "suitability":
            matched, detail = _compare_suitability(fn_val, tb_val)
        elif kind == "date":
            matched, detail = _compare_date(fn_val, tb_val)
        else:
            matched, detail = _compare_code(fn_val, tb_val)
        comparisons.append(
            FieldComparison(
                name=name,
                filename_value=fn_val,
                titleblock_value=tb_val,
                matched=matched,
                detail=detail,
            )
        )

    add("document_reference", filename.document_reference, titleblock.document_reference, "code")
    add("revision", filename.revision, titleblock.revision, "code")
    add("title", filename.title, titleblock.title, "title")
    add("suitability", filename.suitability, titleblock.suitability, "suitability")
    add("date", filename.date, titleblock.date, "date")

    required_fail = False
    mismatch = False
    incomplete = False

    by_name = {item.name: item for item in comparisons}
    for field_name, rule in rules.items():
        if field_name.startswith("history"):
            continue
        item = by_name.get(field_name)
        if item is None:
            continue
        if rule == "required":
            if item.matched is None:
                if filename.parse_ok or item.filename_value is not None:
                    incomplete = True
                    notes.append(f"{field_name}: {item.detail}")
            elif item.matched is False:
                mismatch = True
                required_fail = True
        elif rule in {"if_both_present", "optional"}:
            if item.matched is False:
                mismatch = True

    history_comps, history_mismatch, history_notes = compare_history(titleblock)
    notes.extend(history_notes)

    if _layout_undetected(titleblock):
        return comparisons, history_comps, CheckStatus.UNDETECTED, titleblock.notes
    if not filename.parse_ok:
        return (
            comparisons,
            history_comps,
            CheckStatus.FILENAME_PARSE_ERROR,
            notes + filename.notes + titleblock.notes,
        )
    if incomplete and not required_fail:
        return comparisons, history_comps, CheckStatus.INCOMPLETE, notes + titleblock.notes
    if mismatch:
        return comparisons, history_comps, CheckStatus.MISMATCH, notes
    if history_mismatch:
        return comparisons, history_comps, CheckStatus.HISTORY_MISMATCH, notes
    return comparisons, history_comps, CheckStatus.MATCH, notes


def build_result(result: DocumentResult, rules: dict[str, str]) -> DocumentResult:
    comparisons, history_comps, status, notes = compare_document(
        result.filename, result.titleblock, rules
    )
    result.comparisons = comparisons
    result.history_comparisons = history_comps
    result.status = status
    result.confidence = Confidence.HIGH if status == CheckStatus.MATCH else Confidence.REVIEW
    result.notes = list(
        dict.fromkeys(result.notes + notes + result.filename.notes + result.titleblock.notes)
    )
    return result
