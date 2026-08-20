"""Apply suggested filename changes to PDFs and paired DWG files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from drawing_qa.models import DocumentResult


@dataclass
class RenameStats:
    renamed: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def apply_renames(results: list[DocumentResult], *, verbose: bool = True) -> RenameStats:
    """Rename each result to its suggested_filename when that name differs.

    Records original_filename and rename_result on every item passed in.
    """
    stats = RenameStats()
    for result in results:
        if not result.original_filename:
            result.original_filename = result.path.name

        target_name = result.suggested_filename
        if not target_name:
            result.rename_result = "Not renamed — no title-block document reference"
            stats.skipped += 1
            continue

        if target_name == result.path.name:
            result.rename_result = "Unchanged"
            stats.unchanged += 1
            continue

        new_pdf_path = result.path.parent / target_name
        if new_pdf_path.exists() and not _same_file(new_pdf_path, result.path):
            result.rename_result = f"Not renamed — {target_name} already exists"
            stats.skipped += 1
            if verbose:
                print(f"⚠️  Cannot rename {result.path.name}: {target_name} already exists")
            continue

        original_name = result.path.name
        try:
            result.path.rename(new_pdf_path)
            result.path = new_pdf_path
            result.notes.append(f"Renamed from {original_name} to {target_name}")
            dwg_note = _rename_paired_dwg(result, target_name, verbose=verbose)
            if dwg_note:
                result.rename_result = f"Renamed ({dwg_note})"
            else:
                result.rename_result = "Renamed"
            stats.renamed += 1
            if verbose:
                print(f"✓ Renamed: {original_name} → {target_name}")
        except OSError as exc:
            result.rename_result = f"Failed — {exc}"
            stats.failed += 1
            if verbose:
                print(f"✗ Error renaming {original_name}: {exc}")

    return stats


def _rename_paired_dwg(result: DocumentResult, pdf_target_name: str, *, verbose: bool) -> str | None:
    if not result.paired_dwg or not result.paired_dwg.exists():
        return None

    dwg_name = Path(pdf_target_name).stem + result.paired_dwg.suffix
    new_dwg_path = result.paired_dwg.parent / dwg_name
    if dwg_name == result.paired_dwg.name:
        return None
    if new_dwg_path.exists() and not _same_file(new_dwg_path, result.paired_dwg):
        note = f"DWG not renamed — {dwg_name} already exists"
        result.notes.append(note)
        if verbose:
            print(f"  ⚠️  {note}")
        return note

    original_dwg = result.paired_dwg.name
    try:
        result.paired_dwg.rename(new_dwg_path)
        result.paired_dwg = new_dwg_path
        result.notes.append(f"Renamed DWG from {original_dwg} to {dwg_name}")
        if verbose:
            print(f"  ✓ Renamed DWG: {original_dwg} → {dwg_name}")
    except OSError as exc:
        note = f"DWG not renamed — {exc}"
        result.notes.append(note)
        if verbose:
            print(f"  ⚠️  {note}")
        return note
    return None
