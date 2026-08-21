"""DWG file pairing detection and validation.

Pairs a PDF with a DWG when the ISO 19650 document reference matches, even if
one name has a title and/or revision and the other does not.
"""

from __future__ import annotations

from pathlib import Path

from drawing_qa.docref import parse_name_without_ext
from drawing_qa.models import DocumentResult


def find_dwg_files(folder: Path) -> list[Path]:
    """Find all DWG files in a folder."""
    dwgs = []
    for ext in (".dwg", ".DWG"):
        dwgs.extend(folder.glob(f"*{ext}"))
    return sorted(dwgs)


def _doc_ref_key(stem: str) -> str | None:
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


def find_paired_dwg(pdf_path: Path, dwg_files: list[Path]) -> tuple[Path | None, bool]:
    """Find the DWG that belongs with this PDF.

    Returns (path, names_differ). names_differ is True when a pair was found
    but the stems are not identical (case-insensitive).
    """
    pdf_stem = pdf_path.stem
    for dwg in dwg_files:
        if dwg.stem.lower() == pdf_stem.lower():
            return dwg, False

    pdf_ref = _doc_ref_key(pdf_stem)
    if pdf_ref:
        candidates = [
            dwg for dwg in dwg_files if _doc_ref_key(dwg.stem) == pdf_ref
        ]
        if candidates:
            best = max(candidates, key=lambda dwg: _name_closeness(pdf_stem, dwg.stem))
            return best, True

    return None, False


def check_dwg_pairing(
    results: list[DocumentResult],
    folder: Path,
) -> list[DocumentResult]:
    """Update results with paired_dwg / dwg_mismatch and notes."""
    dwg_files = find_dwg_files(folder)
    for result in results:
        result.dwg_files_present = bool(dwg_files)
        if not dwg_files:
            continue
        paired_dwg, has_mismatch = find_paired_dwg(result.path, dwg_files)
        if paired_dwg:
            result.paired_dwg = paired_dwg
            result.dwg_mismatch = has_mismatch
            if has_mismatch:
                note = (
                    f"DWG paired by document reference: PDF '{result.path.name}' "
                    f"with DWG '{paired_dwg.name}'"
                )
                result.notes.append(note)
        else:
            result.notes.append("No matching DWG in this folder")
    return results
