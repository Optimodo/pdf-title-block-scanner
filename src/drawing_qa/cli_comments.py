"""QA-TB-Comments-Organiser — copy marked-up PDFs into Sorted/{revision}."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from drawing_qa.comments import (
    SORTED_ROOT,
    UNSORTED_NAME,
    _revision_folders,
    organise_comment_pdfs,
    write_comments_report,
)
from drawing_qa.config_loader import load_config
from drawing_qa.paths import app_dir, is_frozen, resolve_config_dir
from drawing_qa.version import TOOL_COMMENTS, tool_banner


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog or TOOL_COMMENTS,
        description=(
            "Copy commented drawing PDFs into Sorted/{revision} using the title-block "
            "revision. Originals stay in the dump folder. Drawings with no readable "
            "P/C revision go to Sorted/Unsorted."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help=(
            "Folder of commented PDFs, or one or more PDF files "
            "(default: folder containing this program)."
        ),
    )
    parser.add_argument(
        "--sorted-dir",
        default=SORTED_ROOT,
        metavar="NAME",
        help=f"Folder name to create for copies (default: {SORTED_ROOT}).",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Override title-block layouts (default: config\\ next to the exe, else bundled).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Excel transmittal (default: Comments_Organiser_ddmmyy.xlsx in the dump folder)."
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
    return parser


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


def resolve_targets(
    inputs: list[Path],
    default_folder: Path,
) -> tuple[Path, list[Path] | None]:
    """Folder to report in, plus an optional PDF subset (dropped files)."""
    if not inputs:
        return default_folder.resolve(), None
    resolved = [path.resolve() for path in inputs]
    dirs = [path for path in resolved if path.is_dir()]
    pdfs = [
        path
        for path in resolved
        if path.is_file() and path.suffix.lower() == ".pdf"
    ]
    if dirs:
        return dirs[0], None
    if pdfs:
        return pdfs[0].parent, pdfs
    first = resolved[0]
    if first.is_file():
        return first.parent, None
    return default_folder.resolve(), None


def run_organise(
    folder: Path,
    *,
    config_dir: Path | None = None,
    sorted_name: str = SORTED_ROOT,
    output: Path | None = None,
    pdfs: list[Path] | None = None,
) -> int:
    folder = folder.resolve()
    if not folder.is_dir():
        print(f"Not a folder: {folder}")
        return 2
    config = load_config(resolve_config_dir(folder, config_dir))
    print(tool_banner(TOOL_COMMENTS))
    print(f"Folder: {folder}")
    print("Reading title-block revisions (same layouts as QA-TB-Checker)...")
    print()

    def on_pdf(index: int, total: int, item) -> None:
        status = item.folder_name if item.copied else "ERROR"
        print(f"[{index}/{total}] {item.source.name} -> {status}", flush=True)

    result = organise_comment_pdfs(
        folder,
        config,
        sorted_name=sorted_name,
        pdfs=pdfs,
        on_pdf=on_pdf,
    )
    if not result.items:
        print("No PDFs found in this folder.")
        return 0
    print()
    counts = result.counts()
    for name in _revision_folders(result):
        label = "Not identified" if name == UNSORTED_NAME else name
        print(f"  {label}: {counts[name]}")
    print(f"  Total: {len(result.items)}")
    saved = write_comments_report(result, output)
    print()
    print(f"Originals left in: {folder}")
    print(f"Copies: {result.sorted_root}")
    print(f"Report: {saved}")
    unsorted = counts.get(UNSORTED_NAME, 0)
    return 1 if unsorted else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    folder, pdfs = resolve_targets(list(args.inputs), app_dir())
    try:
        code = run_organise(
            folder,
            config_dir=args.config_dir,
            sorted_name=args.sorted_dir,
            output=args.output,
            pdfs=pdfs,
        )
    except Exception as exc:  # noqa: BLE001 - show a readable console error
        print(f"ERROR: {exc}")
        code = 2
    if _should_pause(args):
        _pause()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
