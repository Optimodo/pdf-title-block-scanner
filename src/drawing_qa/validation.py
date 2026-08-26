"""Additional validation checks for drawing sets."""

from __future__ import annotations

import re
from collections import defaultdict

from drawing_qa.docref import canonical_doc_ref
from drawing_qa.models import CheckStatus, DocumentResult, record_issue
from drawing_qa.tokens import parse_date, revision_rank


def check_duplicates(results: list[DocumentResult]) -> list[DocumentResult]:
    """Check for duplicate document references across results.
    
    Updates status to DUPLICATE_REFERENCE and adds notes for duplicates.
    Only flags if document reference is successfully extracted.
    
    Args:
        results: List of document results to check
        
    Returns:
        Updated list of results with duplicate flags
    """
    # Group by document reference
    ref_groups: dict[str, list[DocumentResult]] = defaultdict(list)
    
    for result in results:
        doc_ref = canonical_doc_ref(result.titleblock.document_reference)
        if doc_ref:
            ref_groups[doc_ref].append(result)
    
    # Flag duplicates
    for doc_ref, group in ref_groups.items():
        if len(group) > 1:
            filenames = [r.path.name for r in group]
            note = f"Duplicate document reference {doc_ref} found in: {', '.join(filenames)}"
            for result in group:
                record_issue(result, CheckStatus.DUPLICATE_REFERENCE)
                result.notes.append(note)
    
    return results


def check_date_regression(results: list[DocumentResult]) -> list[DocumentResult]:
    """Check for date regression within revision history.

    Later revisions must have later or equal dates within the P series and
    within the C series. The main title-block date is not compared here
    (it may be the original issue date or the latest revision date).
    Updates status to DATE_REGRESSION if issues found.
    
    Args:
        results: List of document results to check
        
    Returns:
        Updated list of results with date regression flags
    """
    for result in results:
        history = result.titleblock.history
        if not history or not history.rows or len(history.rows) < 2:
            continue
        
        dated_rows = []
        for row in history.rows:
            if not row.date:
                continue
            parsed = parse_date(row.date)
            if parsed is None:
                continue
            dated_rows.append((row, parsed))

        by_series: dict[str, list] = defaultdict(list)
        for row, parsed in dated_rows:
            token = (row.revision or "?").strip().upper()
            series = token[0] if token else "?"
            by_series[series].append((row, parsed))

        regression_found = False
        for items in by_series.values():
            items.sort(key=lambda item: revision_rank(item[0].revision))
            for (prev_row, prev_date), (row, current_date) in zip(items, items[1:]):
                if current_date < prev_date:
                    regression_found = True
                    note = (
                        f"Date regression in history: {row.revision} dated {row.date} "
                        f"is before {prev_row.revision} dated {prev_row.date}"
                    )
                    result.notes.append(note)

        if regression_found:
            record_issue(result, CheckStatus.DATE_REGRESSION)
    
    return results


def _document_references_differ(result: DocumentResult) -> bool:
    """True when the filename document reference disagrees with the title block."""
    for item in result.comparisons:
        if item.name == "document_reference":
            return item.matched is False
    filename_ref = canonical_doc_ref(result.filename.document_reference)
    titleblock_ref = canonical_doc_ref(result.titleblock.document_reference)
    if not filename_ref or not titleblock_ref:
        return False
    return filename_ref != titleblock_ref


def _replace_doc_ref_in_stem(stem: str, old_ref: str, new_ref: str) -> str | None:
    """Replace the first occurrence of the filename doc ref, keeping any suffix."""
    seen: list[str] = []
    for candidate in (old_ref, old_ref.replace("-", "_")):
        if candidate and candidate not in seen:
            seen.append(candidate)
    for old in seen:
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        if pattern.search(stem):
            return pattern.sub(new_ref, stem, count=1)
    return None


def suggest_filename(result: DocumentResult) -> str | None:
    """Suggest a filename that swaps in the title-block document reference.

    Only offered when the parsed filename document reference disagrees with the
    title block. Title, revision, and any other trailing text already in the
    name are kept. Does not strip names down to the document reference alone,
    and does not inject title-block title/revision into the name.
    """
    tb_ref = result.titleblock.document_reference
    fn_ref = result.filename.document_reference
    if not tb_ref or not fn_ref:
        return None
    if not _document_references_differ(result):
        return None

    new_stem = _replace_doc_ref_in_stem(result.path.stem, fn_ref, tb_ref)
    if not new_stem:
        return None
    suggested = f"{new_stem}{result.path.suffix}"
    return suggested if suggested != result.path.name else None


def clean_filename_part(text: str) -> str:
    """Make a title-block value safe to use in a Windows filename."""
    cleaned = text.replace("/", "-").replace("\\", "-")
    cleaned = re.sub(r'[<>:"|?*]', "", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip(" .")


def standardize_filename(result: DocumentResult) -> str | None:
    """Build {doc-ref}_{title}_{revision} from the title block.

    Used by TBCheckRename to bulk-rename every PDF that has a readable
    document reference. Missing title or revision is omitted rather than
    blocking the rename. Returns the canonical name even when it already
    matches the current file (so the report can mark it Unchanged).
    """
    tb = result.titleblock
    if not tb.document_reference:
        return None

    parts = [tb.document_reference]
    if tb.title:
        title = clean_filename_part(tb.title)
        if title:
            parts.append(title)
    if tb.revision:
        revision = clean_filename_part(tb.revision)
        if revision:
            parts.append(revision)

    if len(parts) == 1:
        stem = parts[0]
    else:
        stem = "_".join(parts)
    return f"{stem}{result.path.suffix or '.pdf'}"
