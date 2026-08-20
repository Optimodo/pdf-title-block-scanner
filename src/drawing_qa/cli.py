from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawing_qa.checker import check_pdf, check_paths, iter_pdfs
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
from drawing_qa.report import write_report


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
        "--auto-rename",
        action="store_true",
        help="Automatically rename mismatched files without prompting.",
    )
    parser.add_argument(
        "--include-title",
        action="store_true",
        help="Include title in suggested/renamed filenames.",
    )
    parser.add_argument(
        "--include-revision",
        action="store_true",
        help="Include revision in suggested/renamed filenames.",
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


def _print_mismatch_summary(results) -> list:
    """Print summary of mismatches and return list of renameable items."""
    from drawing_qa.models import CheckStatus
    
    mismatches = [
        r for r in results
        if r.status == CheckStatus.MISMATCH and r.suggested_filename
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
    print("Would you like to rename these files to match their title blocks?")
    print("This will rename PDFs (and paired DWG files) to the suggested names.")
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


def _perform_renames(mismatches: list) -> tuple[int, int]:
    """Perform the actual file renames.
    
    Returns tuple of (success_count, error_count).
    """
    success_count = 0
    error_count = 0
    
    for result in mismatches:
        if not result.suggested_filename:
            continue
        
        new_pdf_path = result.path.parent / result.suggested_filename
        
        # Check if target already exists
        if new_pdf_path.exists():
            print(f"⚠️  Cannot rename {result.path.name}: {result.suggested_filename} already exists")
            error_count += 1
            continue
        
        try:
            # Rename PDF
            result.path.rename(new_pdf_path)
            print(f"✓ Renamed: {result.path.name} → {result.suggested_filename}")
            success_count += 1
            
            # Rename paired DWG if exists
            if result.paired_dwg and result.paired_dwg.exists():
                dwg_suggestion = Path(result.suggested_filename).stem + result.paired_dwg.suffix
                new_dwg_path = result.paired_dwg.parent / dwg_suggestion
                
                if new_dwg_path.exists():
                    print(f"  ⚠️  DWG already exists: {dwg_suggestion}")
                else:
                    result.paired_dwg.rename(new_dwg_path)
                    print(f"  ✓ Renamed DWG: {result.paired_dwg.name} → {dwg_suggestion}")
        
        except Exception as e:
            print(f"✗ Error renaming {result.path.name}: {e}")
            error_count += 1
    
    return success_count, error_count


def run_folder_check(
    folder: Path,
    *,
    config_dir: Path | None = None,
    output: Path | None = None,
    recursive: bool = False,
    progress: bool = True,
    auto_rename: bool = False,
    include_title: bool = False,
    include_revision: bool = False,
) -> int:
    folder = folder.resolve()
    config_path = resolve_config_dir(folder, config_dir)
    print("=" * 60)
    print("TBCheck - Title-block QA")
    print("=" * 60)
    print(f"Folder: {folder}")
    print(f"Config: {config_path}")
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
    
    # Check all PDFs first
    initial_results = []
    for index, path in enumerate(pdfs, start=1):
        if progress:
            print(f"[{index}/{len(pdfs)}] {path.name} ...", flush=True)
        result = check_pdf(path, config)
        initial_results.append(result)
        if progress:
            print(f"         {result.status.value}")
    print()
    
    # Apply cross-document validations with filename suggestion options
    results = check_paths(
        pdfs,
        config,
        suggest_title=include_title,
        suggest_revision=include_revision,
    )

    report_path = output if output is not None else next_available_report_path(folder, REPORT_NAME)
    saved = write_report(results, report_path)
    _print_summary(results)
    print(f"Report: {saved}")
    
    # Handle renaming based on mode
    mismatches = _print_mismatch_summary(results)
    
    if auto_rename and mismatches:
        # Automatic rename without prompting
        print()
        print("Auto-renaming files...")
        success, errors = _perform_renames(mismatches)
        print()
        print(f"Renamed {success} file(s) successfully")
        if errors:
            print(f"Failed to rename {errors} file(s)")
    elif progress and mismatches:
        # Interactive mode: offer to rename
        if _offer_rename(mismatches):
            print()
            print("Renaming files...")
            success, errors = _perform_renames(mismatches)
            print()
            print(f"Renamed {success} file(s) successfully")
            if errors:
                print(f"Failed to rename {errors} file(s)")
    
    problems = sum(1 for item in results if item.status.value != "MATCH")
    return 1 if problems else 0


def cmd_check(args: argparse.Namespace) -> int:
    auto_rename = getattr(args, "auto_rename", False)
    include_title = getattr(args, "include_title", False)
    include_revision = getattr(args, "include_revision", False)
    
    target = args.input.resolve() if args.input is not None else app_dir()
    if target.is_file():
        config = load_config(resolve_config_dir(target.parent, args.config_dir))
        pdfs = iter_pdfs(target)
        results = check_paths(pdfs, config, include_title, include_revision)
        output = args.output or next_available_report_path(target.parent, REPORT_NAME)
        saved = write_report(results, output)
        _print_summary(results)
        print(f"Report: {saved}")
        problems = sum(1 for item in results if item.status.value != "MATCH")
        return 1 if problems else 0
    return run_folder_check(
        target,
        config_dir=args.config_dir,
        output=args.output,
        recursive=args.recursive,
        progress=True,
        auto_rename=auto_rename,
        include_title=include_title,
        include_revision=include_revision,
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
    
    # Set defaults for flags if not present (for when called without command)
    if not hasattr(args, "auto_rename"):
        args.auto_rename = False
    if not hasattr(args, "include_title"):
        args.include_title = False
    if not hasattr(args, "include_revision"):
        args.include_revision = False

    code = 0
    try:
        if args.command is None:
            code = run_folder_check(
                app_dir(),
                auto_rename=args.auto_rename,
                include_title=args.include_title,
                include_revision=args.include_revision,
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
