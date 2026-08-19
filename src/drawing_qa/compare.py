from __future__ import annotations

import re

from drawing_qa.models import CheckStatus, DocumentResult, FieldComparison, FilenameFields, TitleBlockFields


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


def _compare_code(filename_value: str | None, titleblock_value: str | None) -> tuple[bool | None, str]:
    left = normalize_code(filename_value)
    right = normalize_code(titleblock_value)
    if left is None and right is None:
        return None, "both empty"
    if left is None:
        return None, "missing in filename"
    if right is None:
        return None, "missing in title block"
    return left == right, "equal" if left == right else f"{left} != {right}"


def _compare_title(filename_value: str | None, titleblock_value: str | None) -> tuple[bool | None, str]:
    left = normalize_title(filename_value)
    right = normalize_title(titleblock_value)
    if left is None and right is None:
        return None, "both empty"
    if left is None:
        return None, "missing in filename"
    if right is None:
        return None, "missing in title block"
    return left == right, "equal" if left == right else f"{left} != {right}"


def _layout_undetected(titleblock: TitleBlockFields) -> bool:
    if not titleblock.layout_id:
        return True
    if titleblock.document_reference is None and titleblock.revision is None:
        return any("below threshold" in note for note in titleblock.notes)
    return False


def compare_document(
    filename: FilenameFields,
    titleblock: TitleBlockFields,
    rules: dict[str, str],
) -> tuple[list[FieldComparison], CheckStatus, list[str]]:
    comparisons: list[FieldComparison] = []
    notes: list[str] = []

    def add(name: str, fn_val: str | None, tb_val: str | None, kind: str) -> None:
        if kind == "title":
            matched, detail = _compare_title(fn_val, tb_val)
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

    required_fail = False
    mismatch = False
    incomplete = False

    by_name = {item.name: item for item in comparisons}
    for field_name, rule in rules.items():
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
        elif rule == "if_both_present":
            if item.matched is False:
                mismatch = True
        elif rule == "optional":
            if item.matched is False:
                mismatch = True

    if _layout_undetected(titleblock):
        return comparisons, CheckStatus.UNDETECTED, titleblock.notes
    if not filename.parse_ok:
        return comparisons, CheckStatus.FILENAME_PARSE_ERROR, notes + filename.notes + titleblock.notes
    if incomplete and not required_fail:
        return comparisons, CheckStatus.INCOMPLETE, notes + titleblock.notes
    if mismatch:
        return comparisons, CheckStatus.MISMATCH, notes
    return comparisons, CheckStatus.MATCH, notes


def build_result(result: DocumentResult, rules: dict[str, str]) -> DocumentResult:
    comparisons, status, notes = compare_document(result.filename, result.titleblock, rules)
    result.comparisons = comparisons
    result.status = status
    result.notes = list(dict.fromkeys(result.notes + notes + result.filename.notes + result.titleblock.notes))
    return result
