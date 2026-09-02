"""DWG file pairing detection and validation.

Pairs a PDF with a DWG when the ISO 19650 document reference matches, even if
one name has a title and/or revision and the other does not.
"""

from __future__ import annotations

from pathlib import Path

from drawing_qa.docref import canonical_doc_ref, parse_name_without_ext, sheet_suffix_style
from drawing_qa.models import CheckStatus, DocumentResult, record_issue

# dwg_issue values
MISSING = "missing"
SHEET_SUFFIX = "sheet_suffix"
NAME_DIFFERS = "name_differs"


def find_dwg_files(folder: Path) -> list[Path]:
    """Find all DWG files in a folder.

    Windows glob is case-insensitive, so ``*.dwg`` and ``*.DWG`` would otherwise
    count each file twice.
    """
    seen: dict[str, Path] = {}
    try:
        entries = folder.iterdir()
    except OSError:
        return []
    for path in entries:
        if not path.is_file() or path.suffix.lower() != ".dwg":
            continue
        key = str(path.resolve()).casefold()
        if key not in seen:
            seen[key] = path
    return sorted(seen.values(), key=lambda item: item.name.casefold())


def _doc_ref_key(stem: str) -> str | None:
    parsed = parse_name_without_ext(stem)
    if parsed and parsed.doc_ref:
        return canonical_doc_ref(parsed.doc_ref)
    return None


def _raw_doc_ref(stem: str) -> str | None:
    parsed = parse_name_without_ext(stem)
    if parsed and parsed.doc_ref:
        return parsed.doc_ref.upper()
    return None


def _name_closeness(pdf_stem: str, dwg_stem: str) -> tuple[int, int]:
    """Higher is closer: exact stem, then longest common prefix."""
    left, right = pdf_stem.lower(), dwg_stem.lower()
    if left == right:
        return (2, len(left))
    n = 0
    for a, b in zip(left, right, strict=False):
        if a != b:
            break
        n += 1
    return (1, n)


def _sheet_suffix_mismatch(pdf_stem: str, dwg_stem: str) -> bool:
    pdf_ref, dwg_ref = _raw_doc_ref(pdf_stem), _raw_doc_ref(dwg_stem)
    if not pdf_ref or not dwg_ref:
        return False
    if canonical_doc_ref(pdf_ref) != canonical_doc_ref(dwg_ref):
        return False
    pdf_style, dwg_style = sheet_suffix_style(pdf_ref), sheet_suffix_style(dwg_ref)
    return bool(pdf_style and dwg_style and pdf_style != dwg_style)


def find_paired_dwg(pdf_path: Path, dwg_files: list[Path]) -> tuple[Path | None, str | None]:
    """Find the DWG that belongs with this PDF.

    Returns (path, issue). issue is None when stems match, otherwise
    ``sheet_suffix`` (.1 vs -1) or ``name_differs``.
    """
    pdf_stem = pdf_path.stem
    for dwg in dwg_files:
        if dwg.stem.lower() == pdf_stem.lower():
            return dwg, None

    pdf_ref = _doc_ref_key(pdf_stem)
    if pdf_ref:
        candidates = [dwg for dwg in dwg_files if _doc_ref_key(dwg.stem) == pdf_ref]
        if candidates:
            best = max(candidates, key=lambda dwg: _name_closeness(pdf_stem, dwg.stem))
            if _sheet_suffix_mismatch(pdf_stem, best.stem):
                return best, SHEET_SUFFIX
            return best, NAME_DIFFERS

    return None, None


def unpaired_dwgs(results: list[DocumentResult], dwg_files: list[Path]) -> list[Path]:
    paired = {result.paired_dwg.resolve() for result in results if result.paired_dwg}
    return [dwg for dwg in dwg_files if dwg.resolve() not in paired]


def check_dwg_pairing(
    results: list[DocumentResult],
    folder: Path,
    *,
    flag_issues: bool = True,
) -> list[DocumentResult]:
    """Update results with paired_dwg / dwg_mismatch / dwg_issue and notes."""
    dwg_files = find_dwg_files(folder)
    for result in results:
        result.dwg_files_present = bool(dwg_files)
        result.dwg_issue = None
        if not dwg_files:
            continue
        paired_dwg, issue = find_paired_dwg(result.path, dwg_files)
        if paired_dwg:
            result.paired_dwg = paired_dwg
            result.dwg_mismatch = issue is not None
            result.dwg_issue = issue
            if issue == SHEET_SUFFIX:
                pdf_ref = _raw_doc_ref(result.path.stem) or result.path.stem
                dwg_ref = _raw_doc_ref(paired_dwg.stem) or paired_dwg.stem
                note = (
                    f"DWG sheet number punctuation differs: PDF '{pdf_ref}' "
                    f"vs DWG '{dwg_ref}' (.1 vs -1)"
                )
                result.notes.append(note)
                if flag_issues:
                    record_issue(result, CheckStatus.DWG_ISSUE)
            elif issue == NAME_DIFFERS:
                result.notes.append(
                    f"DWG paired by document reference: PDF '{result.path.name}' "
                    f"with DWG '{paired_dwg.name}'"
                )
        else:
            result.dwg_issue = MISSING
            result.notes.append("No matching DWG in this folder")
            if flag_issues:
                record_issue(result, CheckStatus.DWG_ISSUE)
    return results
