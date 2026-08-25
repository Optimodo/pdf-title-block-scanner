from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawing_qa.checker import check_paths, iter_pdfs
from drawing_qa.config_loader import load_config
from drawing_qa.detect import crop_region_pixmap, region_debug_text
from drawing_qa.extract import require_pymupdf
from drawing_qa.paths import (
    REPORT_NAME,
    app_dir,
    is_frozen,
    next_available_report_path,
    resolve_config_dir,
)
from drawing_qa.rename import RenameStats, apply_renames
from drawing_qa.report import write_report
from drawing_qa.timing import format_report as format_timing_report, is_enabled as timing_enabled


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="TBCheck",
        description=(
            "Compare ISO 19650 drawing filenames with title-block contents. "
            "With no arguments, checks every PDF in the folder that contains this program."
        ),
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not wait for Enter before exiting (default when not frozen).",
    )
    parser.add_argument(
        "--pause",
        action="store_true",
        help="Wait for Enter before exiting (default for the standalone exe).",
    )
    parser.add_argument(
        "--standardize-names",
        action="store_true",
        help=(
            "Automatically rename every PDF to document-reference_title_revision "
            "from the title block (TBCheckRename). No prompt."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="Scan PDFs and write an Excel QA report")
    check.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="PDF file or folder of PDFs (default: this program's folder)",
    )
    check.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Folder containing settings.yaml and title_blocks/",
    )
    check.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Excel report path (default: TBCheckReport.xlsx in the target folder)",
    )
    check.add_argument(
        "--recursive",
        action="store_true",
        help="Include PDFs in subfolders",
    )

    inspect = sub.add_parser(
        "inspect",
        help="Dump title-block region text from a PDF to help configure a layout",
    )
    inspect.add_argument("pdf", type=Path)
    inspect.add_argument("--config-dir", type=Path, default=None)
    inspect.add_argument(
        "--debug-dir",
        type=Path,
        default=None,
        help="Where to write cropped title-block images",
    )
    return parser


def _print_summary(results) -> None:
    counts: dict[str, int] = {}
    for item in results:
        counts[item.status.value] = counts.get(item.status.value, 0) + 1
    print(f"Checked {len(results)} PDF(s)")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    paired = sum(1 for item in results if item.paired_dwg)
    missing_dwg = sum(
        1 for item in results if item.dwg_files_present and not item.paired_dwg
    )
    if any(item.dwg_files_present for item in results):
        suffix = sum(1 for item in results if item.dwg_issue == "sheet_suffix")
        names = sum(1 for item in results if item.dwg_issue == "name_differs")
        extra = []
        if suffix:
            extra.append(f"{suffix} .1 vs -1")
        if names:
            extra.append(f"{names} other name difference(s)")
        extra_txt = f" ({', '.join(extra)})" if extra else ""
        print(f"  DWG pairing: {paired} paired, {missing_dwg} missing{extra_txt}")
        print("  See the DWG pairing tab in the Excel report")
    else:
        print("  DWG pairing: no DWG files in this folder")


def _print_mismatch_summary(results) -> list:
    """Print summary of mismatches and return list of renameable items."""
    mismatches = [
        r for r in results
        if r.suggested_filename
    ]
    
    if not mismatches:
        return []
    
    print()
    print("=" * 80)
    print(f"Found {len(mismatches)} file(s) with document reference mismatches:")
    print("=" * 80)
    print()
    
    for i, result in enumerate(mismatches, 1):
        print(f"{i}. {result.path.name}")
        print(f"   Filename doc ref: {result.filename.document_reference or '(none)'}")
        print(f"   Title block doc ref: {result.titleblock.document_reference}")
        if result.suggested_filename:
            print(f"   Suggested: {result.suggested_filename}")
        if result.paired_dwg:
            status = " (naming mismatch)" if result.dwg_mismatch else ""
            print(f"   Paired DWG: {result.paired_dwg.name}{status}")
        print()
    
    return mismatches


def _offer_rename(mismatches: list) -> bool:
    """Offer to rename mismatched files interactively.
    
    Returns True if user wants to rename, False otherwise.
    """
    if not mismatches:
        return False
    
    print("=" * 80)
    print("Would you like to rename these files so the filename document")
    print("reference matches the title block?")
    print("Only the document reference is replaced; any title or revision")
    print("already in the filename is kept. Paired DWG files are renamed too.")
    print("=" * 80)
    
    while True:
        response = input("Rename files? (yes/no/preview): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        if response in ("p", "preview"):
            _preview_renames(mismatches)
            continue
        print("Please answer 'yes', 'no', or 'preview'")


def _preview_renames(mismatches: list) -> None:
    """Show what would be renamed without actually renaming."""
    print()
    print("Preview of changes:")
    print("-" * 80)
    for result in mismatches:
        print(f"PDF: {result.path.name} → {result.suggested_filename}")
        if result.paired_dwg and result.suggested_filename:
            # Suggest DWG name based on PDF suggestion
            dwg_suggestion = Path(result.suggested_filename).stem + ".dwg"
            print(f"DWG: {result.paired_dwg.name} → {dwg_suggestion}")
        print()


def _print_rename_stats(stats: RenameStats) -> None:
    print()
    print(f"Renamed {stats.renamed} file(s)")
    if stats.unchanged:
        print(f"Unchanged {stats.unchanged} file(s) (already matched title-block name)")
    if stats.skipped:
        print(f"Skipped {stats.skipped} file(s)")
    if stats.failed:
        print(f"Failed to rename {stats.failed} file(s)")


def run_folder_check(
    folder: Path,
    *,
    config_dir: Path | None = None,
    output: Path | None = None,
    recursive: bool = False,
    progress: bool = True,
    standardize_names: bool = False,
) -> int:
    folder = folder.resolve()
    config_path = resolve_config_dir(folder, config_dir)
    print("=" * 60)
    if standardize_names:
        print("TBCheckRename - Title-block QA + standardize filenames")
    else:
        print("TBCheck - Title-block QA")
    print("=" * 60)
    print(f"Folder: {folder}")
    print(f"Config: {config_path}")
    if standardize_names:
        print("Rename: automatic — document reference + title + revision from the title block")
    print()

    try:
        config = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not load config: {exc}", file=sys.stderr)
        return 2

    pdfs = iter_pdfs(folder, recursive=recursive)
    if not pdfs:
        print("No PDF files found in this folder.")
        return 2

    print(f"Found {len(pdfs)} PDF(s)")
    print()

    def on_pdf(index: int, total: int, result) -> None:
        if progress:
            print(f"[{index}/{total}] {result.path.name} ...", flush=True)
            print(f"         {result.status.value}")

    results = check_paths(
        pdfs, config, standardize=standardize_names, on_pdf=on_pdf
    )
    if progress:
        print()

    if standardize_names:
        print("Renaming files to document-reference_title_revision...")
        stats = apply_renames(results)
        _print_rename_stats(stats)
    else:
        mismatches = _print_mismatch_summary(results)
        if progress and mismatches:
            if _offer_rename(mismatches):
                print()
                print("Renaming files...")
                stats = apply_renames(mismatches)
                _print_rename_stats(stats)
            else:
                for item in mismatches:
                    item.rename_result = "Not renamed"

    report_path = output if output is not None else next_available_report_path(folder, REPORT_NAME)
    saved = write_report(results, report_path)
    _print_summary(results)
    print(f"Report: {saved}")
    if timing_enabled():
        print()
        print(format_timing_report())
    
    problems = sum(1 for item in results if item.status.value != "MATCH")
    return 1 if problems else 0


def cmd_check(args: argparse.Namespace) -> int:
    standardize_names = getattr(args, "standardize_names", False)
    target = args.input.resolve() if args.input is not None else app_dir()
    if target.is_file():
        config = load_config(resolve_config_dir(target.parent, args.config_dir))
        pdfs = iter_pdfs(target)
        results = check_paths(pdfs, config, standardize=standardize_names)
        if standardize_names:
            print("Renaming file to document-reference_title_revision...")
            stats = apply_renames(results)
            _print_rename_stats(stats)
        output = args.output or next_available_report_path(target.parent, REPORT_NAME)
        saved = write_report(results, output)
        _print_summary(results)
        print(f"Report: {saved}")
        if timing_enabled():
            print()
            print(format_timing_report())
        problems = sum(1 for item in results if item.status.value != "MATCH")
        return 1 if problems else 0
    return run_folder_check(
        target,
        config_dir=args.config_dir,
        output=args.output,
        recursive=args.recursive,
        progress=True,
        standardize_names=standardize_names,
    )


def cmd_inspect(args: argparse.Namespace) -> int:
    require_pymupdf()
    import pymupdf

    config_path = resolve_config_dir(args.pdf.parent, args.config_dir)
    config = load_config(config_path)
    if not args.pdf.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    debug_dir = args.debug_dir or (args.pdf.parent / "debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(args.pdf) as doc:
        page = doc[0]
        print(f"File: {args.pdf}")
        print(f"Page size: {page.rect.width:.1f} x {page.rect.height:.1f} pt")
        print()
        for layout in config.layouts:
            print(f"=== {layout.id} ({layout.name}) ===")
            print(f"Region: {layout.region}")
            text = region_debug_text(page, layout.region)
            print(text or "(no text in region)")
            print()
            pixmap = crop_region_pixmap(page, layout.region)
            image_path = debug_dir / f"{args.pdf.stem}_{layout.id}.png"
            pixmap.save(str(image_path))
            print(f"Cropped image: {image_path}")
            print()
    return 0


def _should_pause(args: argparse.Namespace) -> bool:
    if args.no_pause:
        return False
    if args.pause:
        return True
    return is_frozen()


def _pause() -> None:
    print()
    try:
        input("Press Enter to exit...")
    except EOFError:
        pass


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    pause_flag = None
    cleaned: list[str] = []
    for item in raw:
        if item == "--no-pause":
            pause_flag = False
        elif item == "--pause":
            pause_flag = True
        else:
            cleaned.append(item)

    parser = build_parser()
    args = parser.parse_args(cleaned)
    if pause_flag is False:
        args.no_pause = True
        args.pause = False
    elif pause_flag is True:
        args.pause = True
        args.no_pause = False
    
    code = 0
    try:
        if args.command is None:
            code = run_folder_check(
                app_dir(),
                standardize_names=getattr(args, "standardize_names", False),
            )
        elif args.command == "check":
            code = cmd_check(args)
        elif args.command == "inspect":
            code = cmd_inspect(args)
        else:
            parser.error(f"Unknown command {args.command}")
            code = 2
    except Exception as exc:  # noqa: BLE001 - keep the console open on unexpected errors
        print(f"ERROR: {exc}", file=sys.stderr)
        code = 2
    if _should_pause(args):
        _pause()
    return code
