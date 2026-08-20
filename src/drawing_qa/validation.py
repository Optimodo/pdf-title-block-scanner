"""Additional validation checks for drawing sets."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from drawing_qa.models import CheckStatus, DocumentResult
from drawing_qa.tokens import parse_date


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
        doc_ref = result.titleblock.document_reference
        if doc_ref and doc_ref.strip():
            ref_groups[doc_ref].append(result)
    
    # Flag duplicates
    for doc_ref, group in ref_groups.items():
        if len(group) > 1:
            filenames = [r.path.name for r in group]
            note = f"Duplicate document reference {doc_ref} found in: {', '.join(filenames)}"
            for result in group:
                # Only override if current status is not more serious
                if result.status in (CheckStatus.MATCH, CheckStatus.SPELLING_ERROR):
                    result.status = CheckStatus.DUPLICATE_REFERENCE
                result.notes.append(note)
    
    return results


def check_date_regression(results: list[DocumentResult]) -> list[DocumentResult]:
    """Check for date regression within revision history.
    
    Validates that later revisions have later or equal dates.
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
        
        # Sort rows by revision to check progression
        # Check if dates go backwards
        prev_date = None
        regression_found = False
        
        for row in history.rows:
            if not row.date:
                continue
                
            current_date = parse_date(row.date)
            if current_date is None:
                continue
            
            if prev_date and current_date < prev_date:
                regression_found = True
                note = f"Date regression in history: {row.revision} dated {row.date} is before previous revision"
                result.notes.append(note)
            
            prev_date = current_date
        
        # Also check current date vs latest history
        if result.titleblock.date and history.latest and history.latest.date:
            current_date = parse_date(result.titleblock.date)
            latest_history_date = parse_date(history.latest.date)
            
            if current_date and latest_history_date and current_date < latest_history_date:
                regression_found = True
                note = f"Current date {result.titleblock.date} is before latest history date {history.latest.date}"
                result.notes.append(note)
        
        if regression_found:
            # Only override if not a more serious issue
            if result.status in (CheckStatus.MATCH, CheckStatus.SPELLING_ERROR):
                result.status = CheckStatus.DATE_REGRESSION
    
    return results


def suggest_filename(
    result: DocumentResult,
    include_title: bool = False,
    include_revision: bool = False,
) -> str | None:
    """Suggest corrected filename based on title block values.
    
    When there's a mismatch, constructs the "correct" filename from
    the title block document reference, optionally with title and revision.
    
    Args:
        result: Document result with mismatch
        include_title: If True, include title in suggested filename
        include_revision: If True, include revision in suggested filename
        
    Returns:
        Suggested filename or None if cannot be determined
    """
    if result.status not in (CheckStatus.MISMATCH, CheckStatus.SPELLING_ERROR):
        return None
    
    tb = result.titleblock
    if not tb.document_reference:
        return None
    
    # Start with document reference (always included)
    parts = [tb.document_reference]
    
    # Add title if requested and available
    if include_title and tb.title:
        # Clean title for filename (remove special chars)
        clean_title = tb.title.replace("/", "-").replace("\\", "-")
        clean_title = " ".join(clean_title.split())  # Normalize whitespace
        parts.append(clean_title)
    
    # Add revision if requested and available
    if include_revision and tb.revision:
        parts.append(tb.revision)
    
    # Construct filename
    if len(parts) == 1:
        # Just document reference
        suggested = f"{parts[0]}.pdf"
    elif len(parts) == 2:
        # Doc ref + one other field
        # Check if second part looks like revision (short, alphanumeric)
        if len(parts[1]) <= 5 and parts[1].replace(" ", "").isalnum():
            suggested = f"{parts[0]}-{parts[1]}.pdf"
        else:
            suggested = f"{parts[0]}_{parts[1]}.pdf"
    else:
        # doc_ref + title + revision
        suggested = f"{parts[0]}_{parts[1]}_{parts[2]}.pdf"
    
    return suggested if suggested != result.path.name else None
