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


def run_folder_check(
    folder: Path,
    *,
    config_dir: Path | None = None,
    output: Path | None = None,
    recursive: bool = False,
    progress: bool = True,
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
    results = []
    for index, path in enumerate(pdfs, start=1):
        if progress:
            print(f"[{index}/{len(pdfs)}] {path.name} ...", flush=True)
        result = check_pdf(path, config)
        results.append(result)
        if progress:
            print(f"         {result.status.value}")
    print()

    report_path = output if output is not None else next_available_report_path(folder, REPORT_NAME)
    saved = write_report(results, report_path)
    _print_summary(results)
    print(f"Report: {saved}")
    problems = sum(1 for item in results if item.status.value != "MATCH")
    return 1 if problems else 0


def cmd_check(args: argparse.Namespace) -> int:
    target = args.input.resolve() if args.input is not None else app_dir()
    if target.is_file():
        config = load_config(resolve_config_dir(target.parent, args.config_dir))
        pdfs = iter_pdfs(target)
        results = check_paths(pdfs, config)
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
            code = run_folder_check(app_dir())
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
