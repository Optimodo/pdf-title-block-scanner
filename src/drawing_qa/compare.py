from __future__ import annotations

import re

from drawing_qa.client import (
    allowed_clients_for_project,
    client_is_allowed,
    client_whitelist_note,
)
from drawing_qa.checks import CheckOptions
from drawing_qa.config_loader import ClientCheckConfig, SpellCheckConfig, SuitabilityCheckConfig
from drawing_qa.models import (
    CheckStatus,
    Confidence,
    DocumentResult,
    FieldComparison,
    FilenameFields,
    TitleBlockFields,
    finalize_status,
    record_issue,
)
from drawing_qa.spellcheck import check_spelling, format_spelling_note
from drawing_qa.suitability import (
    allowed_values_for_project,
    project_has_purpose_list,
    revision_purpose_mismatch_note,
    suitability_is_allowed,
    suitability_whitelist_note,
)
from drawing_qa.timing import span as timing_span
from drawing_qa.docref import canonical_doc_ref
from drawing_qa.history import history_first_row
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


def _compare_doc_ref(left: str | None, right: str | None) -> tuple[bool | None, str]:
    a, b = canonical_doc_ref(left), canonical_doc_ref(right)
    if a is None and b is None:
        return None, "both empty"
    if a is None:
        return None, "missing on left"
    if b is None:
        return None, "missing on right"
    return a == b, "equal" if a == b else f"{a} != {b}"


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


def _compare_history_date(
    current: str | None,
    first_date: str | None,
    latest_date: str | None,
) -> tuple[bool | None, str]:
    """Accept the main date when it matches the first or latest history date."""
    if not current and not first_date and not latest_date:
        return None, "both empty"
    if not current:
        return None, "missing on left"
    if not first_date and not latest_date:
        return None, "missing on right"

    eq_latest = dates_equal(current, latest_date) if latest_date else False
    if eq_latest is True:
        return True, "equals latest history date"
    eq_first = dates_equal(current, first_date) if first_date else False
    if eq_first is True:
        return True, "equals first history date"

    if eq_latest is None and eq_first is not True:
        if not first_date or eq_first is None:
            return None, "unparsed"

    first_label = first_date or "(none)"
    latest_label = latest_date or "(none)"
    if not first_date or dates_equal(first_date, latest_date) is True:
        return False, f"{current} != {latest_label}"
    return False, f"{current} matches neither first {first_label} nor latest {latest_label}"


def _layout_undetected(titleblock: TitleBlockFields) -> bool:
    if not titleblock.layout_id:
        return True
    if titleblock.document_reference is None and titleblock.revision is None:
        return any("below threshold" in note for note in titleblock.notes)
    return False


def _history_copied(titleblock: TitleBlockFields, name: str) -> bool:
    field = titleblock.fields.get(name)
    return bool(field and field.source == "history")


def compare_history(
    titleblock: TitleBlockFields,
    *,
    allowed_suitability: list[str] | None = None,
    accept_code_only: bool = True,
) -> tuple[list[FieldComparison], bool, list[str]]:
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
            if not history_value:
                comparisons.append(
                    FieldComparison(
                        name=f"history_{name}",
                        filename_value=current,
                        titleblock_value=history_value,
                        matched=True,
                        detail="no purpose of issue on latest history row",
                    )
                )
                return
            if allowed_suitability and not suitability_is_allowed(
                history_value,
                allowed_suitability,
                accept_code_only=accept_code_only,
            ):
                comparisons.append(
                    FieldComparison(
                        name=f"history_{name}",
                        filename_value=current,
                        titleblock_value=history_value,
                        matched=True,
                        detail="latest history row is a note, not a purpose of issue",
                    )
                )
                return
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

    first = history_first_row(titleblock.history)
    first_date = first.date if first else None
    if _history_copied(titleblock, "date"):
        comparisons.append(
            FieldComparison(
                name="history_date",
                filename_value=titleblock.date,
                titleblock_value=latest.date,
                matched=True,
                detail="current field taken from latest history row",
            )
        )
    else:
        matched, detail = _compare_history_date(titleblock.date, first_date, latest.date)
        comparisons.append(
            FieldComparison(
                name="history_date",
                filename_value=titleblock.date,
                titleblock_value=latest.date,
                matched=matched,
                detail=detail,
            )
        )

    add("suitability", titleblock.suitability, latest.suitability, "suitability")

    mismatched = False
    for item in comparisons:
        if item.name == "history_revision" and item.matched is False:
            mismatched = True
            notes.append(f"History latest revision {item.titleblock_value} != current {item.filename_value}")
        elif item.name == "history_date" and item.matched is False:
            mismatched = True
            notes.append(f"History date: {item.detail}")
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
    *,
    allowed_suitability: list[str] | None = None,
    accept_code_only: bool = True,
    check_options: CheckOptions | None = None,
) -> tuple[list[FieldComparison], list[FieldComparison], CheckStatus, list[str]]:
    comparisons: list[FieldComparison] = []
    notes: list[str] = []
    options = check_options or CheckOptions()

    def add(name: str, fn_val: str | None, tb_val: str | None, kind: str) -> None:
        if kind == "title":
            matched, detail = _compare_title(fn_val, tb_val)
        elif kind == "suitability":
            matched, detail = _compare_suitability(fn_val, tb_val)
        elif kind == "date":
            matched, detail = _compare_date(fn_val, tb_val)
        elif kind == "doc_ref":
            matched, detail = _compare_doc_ref(fn_val, tb_val)
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

    add("document_reference", filename.document_reference, titleblock.document_reference, "doc_ref")
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
                if options.allows("mismatch"):
                    mismatch = True
                    required_fail = True
                    notes.append(
                        f"{field_name.replace('_', ' ')} mismatch: "
                        f"filename {item.filename_value!r} != title block {item.titleblock_value!r}"
                    )
        elif rule in {"if_both_present", "optional"}:
            if item.matched is False and options.allows("mismatch"):
                mismatch = True
                notes.append(
                    f"{field_name.replace('_', ' ')} mismatch: "
                    f"filename {item.filename_value!r} != title block {item.titleblock_value!r}"
                )

    history_comps, history_mismatch, history_notes = compare_history(
        titleblock,
        allowed_suitability=allowed_suitability,
        accept_code_only=accept_code_only,
    )
    if options.allows("history"):
        notes.extend(history_notes)
    else:
        history_mismatch = False

    if _layout_undetected(titleblock):
        return comparisons, history_comps, CheckStatus.UNDETECTED, titleblock.notes
    if not filename.parse_ok and options.allows("filename-parse"):
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


def build_result(
    result: DocumentResult,
    rules: dict[str, str],
    spell_check_config: SpellCheckConfig | None = None,
    suitability_check_config: SuitabilityCheckConfig | None = None,
    client_check_config: ClientCheckConfig | None = None,
    check_options: CheckOptions | None = None,
) -> DocumentResult:
    allowed: list[str] = []
    accept_code_only = True
    if suitability_check_config and suitability_check_config.enabled:
        project = result.filename.parts.get("project")
        allowed = allowed_values_for_project(
            project,
            suitability_check_config.values,
            suitability_check_config.projects,
            suggested=suitability_check_config.suggested,
        )
        accept_code_only = suitability_check_config.accept_code_only
        result.allowed_suitability = list(allowed)
        official = project_has_purpose_list(project, suitability_check_config.projects)
        result.purpose_list_official = official
        if project:
            result.purpose_list_name = suitability_check_config.project_names.get(
                project.strip().upper(), ""
            )
        result.designer_purpose_values = list(allowed)

    options = check_options or CheckOptions()
    comparisons, history_comps, status, notes = compare_document(
        result.filename,
        result.titleblock,
        rules,
        allowed_suitability=allowed or None,
        accept_code_only=accept_code_only,
        check_options=options,
    )
    result.comparisons = comparisons
    result.history_comparisons = history_comps
    result.status = status
    result.confidence = Confidence.HIGH if status == CheckStatus.MATCH else Confidence.REVIEW
    result.notes = list(
        dict.fromkeys(result.notes + notes + result.filename.notes + result.titleblock.notes)
    )
    if status != CheckStatus.MATCH:
        record_issue(result, status)

    # Run spell checking if enabled
    if (
        options.allows("spelling")
        and spell_check_config
        and spell_check_config.enabled
        and spell_check_config.check_title
    ):
        title_to_check = result.titleblock.title
        if title_to_check:
            with timing_span("spellcheck"):
                try:
                    misspelled, suggestions = check_spelling(
                        title_to_check,
                        language=spell_check_config.language,
                    )
                except Exception as exc:  # noqa: BLE001 - never abort a folder scan for spellcheck
                    result.notes.append(f"Spell check skipped: {exc}")
                    misspelled, suggestions = [], []
            if misspelled:
                result.spelling_errors = misspelled
                spell_note = format_spelling_note(misspelled, suggestions)
                result.notes.append(spell_note)
                if spell_check_config.fail_on_error:
                    record_issue(result, CheckStatus.SPELLING_ERROR)

    if (
        options.allows("suitability")
        and suitability_check_config
        and suitability_check_config.enabled
        and result.titleblock.suitability
        and result.allowed_suitability
        and not suitability_is_allowed(
            result.titleblock.suitability,
            result.allowed_suitability,
            accept_code_only=suitability_check_config.accept_code_only,
        )
    ):
        result.notes.append(suitability_whitelist_note(result.titleblock.suitability))
        if suitability_check_config.fail_on_error:
            record_issue(result, CheckStatus.SUITABILITY_ERROR)

    purpose_enabled = True
    purpose_review = None
    purpose_construction = None
    if suitability_check_config is not None:
        purpose_enabled = suitability_check_config.purpose_enabled
        purpose_review = suitability_check_config.purpose_review
        purpose_construction = suitability_check_config.purpose_construction
    if purpose_enabled and options.allows("purpose"):
        purpose_note = revision_purpose_mismatch_note(
            result.titleblock.revision,
            result.titleblock.suitability,
            review=purpose_review,
            construction=purpose_construction,
        )
        if purpose_note:
            result.notes.append(purpose_note)
            record_issue(result, CheckStatus.PURPOSE_MISMATCH)

    if (
        options.allows("client")
        and client_check_config
        and client_check_config.enabled
        and CheckStatus.UNDETECTED not in result.issues
        and result.status != CheckStatus.UNDETECTED
    ):
        project = result.filename.parts.get("project")
        allowed_clients = allowed_clients_for_project(
            project, client_check_config.projects
        )
        result.allowed_clients = list(allowed_clients)
        if allowed_clients and not client_is_allowed(
            result.titleblock.client, allowed_clients
        ):
            result.notes.append(
                client_whitelist_note(result.titleblock.client, allowed_clients)
            )
            if client_check_config.fail_on_error:
                record_issue(result, CheckStatus.CLIENT_ERROR)

    finalize_status(result)
    return result
