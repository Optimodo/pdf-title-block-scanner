from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawing_qa.checker import check_paths, iter_pdfs
from drawing_qa.config_loader import load_config
from drawing_qa.detect import crop_region_pixmap, region_debug_text
from drawing_qa.extract import require_pymupdf
from drawing_qa.report import write_report

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config"


def _package_config_dir() -> Path:
    if DEFAULT_CONFIG.is_dir():
        return DEFAULT_CONFIG
    return Path.cwd() / "config"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drawing-qa",
        description="Compare ISO 19650 drawing filenames with title-block contents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Scan PDFs and write an Excel QA report")
    check.add_argument("input", type=Path, help="PDF file or folder of PDFs")
    check.add_argument(
        "--config-dir",
        type=Path,
        default=_package_config_dir(),
        help="Folder containing settings.yaml and title_blocks/",
    )
    check.add_argument(
        "--output",
        type=Path,
        default=Path("reports/titleblock-qa.xlsx"),
        help="Excel report path",
    )

    inspect = sub.add_parser(
        "inspect",
        help="Dump title-block region text from a PDF to help configure a layout",
    )
    inspect.add_argument("pdf", type=Path)
    inspect.add_argument("--config-dir", type=Path, default=_package_config_dir())
    inspect.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("debug"),
        help="Where to write cropped title-block images",
    )
    return parser


def cmd_check(args: argparse.Namespace) -> int:
    config = load_config(args.config_dir)
    pdfs = iter_pdfs(args.input)
    if not pdfs:
        print(f"No PDFs found in {args.input}", file=sys.stderr)
        return 2
    results = check_paths(pdfs, config)
    output = write_report(results, args.output)
    counts: dict[str, int] = {}
    for item in results:
        counts[item.status.value] = counts.get(item.status.value, 0) + 1
    print(f"Checked {len(results)} PDF(s)")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print(f"Report: {output}")
    problems = sum(
        1
        for item in results
        if item.status.value != "MATCH"
    )
    return 1 if problems else 0


def cmd_inspect(args: argparse.Namespace) -> int:
    require_pymupdf()
    import pymupdf

    config = load_config(args.config_dir)
    if not args.pdf.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    args.debug_dir.mkdir(parents=True, exist_ok=True)
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
            image_path = args.debug_dir / f"{args.pdf.stem}_{layout.id}.png"
            pixmap.save(str(image_path))
            print(f"Cropped image: {image_path}")
            print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return cmd_check(args)
    if args.command == "inspect":
        return cmd_inspect(args)
    parser.error(f"Unknown command {args.command}")
    return 2
