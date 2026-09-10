from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from drawing_qa.checker import check_paths, iter_pdfs
from drawing_qa.checks import (
    CheckOptions,
    UnknownCheckError,
    apply_check_toggles,
    format_check_list,
    format_check_menu,
    parse_check_choice,
    resolve_check_options,
)
from drawing_qa.config_loader import load_config
from drawing_qa.detect import crop_region_pixmap, region_debug_text
from drawing_qa.document_list import is_spreadsheet
from drawing_qa.extract import require_pymupdf
from drawing_qa.paths import (
    app_dir,
    designer_report_path,
    designer_text_report_path,
    document_control_report_path,
    is_frozen,
    resolve_config_dir,
)
from drawing_qa.rename import RenameStats, apply_renames
from drawing_qa.report import default_report_path, write_report
from drawing_qa.timing import format_report as format_timing_report, is_enabled as timing_enabled
from drawing_qa.version import TOOL_CHECKER, TOOL_CUSTOM, TOOL_RENAMER, tool_banner


_TOGGLE_VALUE_FLAGS = {
    "--document-list",
    "--disable",
    "--enable",
    "--checks",
    "--config-dir",
    "--output",
    "--debug-dir",
}


def _add_check_toggle_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="CHECKS",
        help="Turn off QA checks (comma-separated ids, or all / portal). Repeatable.",
    )
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        metavar="CHECKS",
        help="Turn on QA checks after --disable or --checks. Repeatable.",
    )
    parser.add_argument(
        "--checks",
        default=None,
        metavar="CHECKS",
        help="Run only these QA checks (comma-separated). All others stay off.",
    )
    parser.add_argument(
        "--list-checks",
        action="store_true",
        help="Print QA check ids that can be toggled, then exit.",
    )
    parser.add_argument(
        "--prompt-checks",
        action="store_true",
        help="Ask which QA checks to run before scanning (QA-TB-Custom-Checker).",
    )
    parser.add_argument(
        "--previews",
        action="store_true",
        help="Include cropped title-block fields on every drawing in the Excel report.",
    )
    parser.add_argument(
        "--custom-checks",
        action="store_true",
        help=argparse.SUPPRESS,
    )


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    toggles = argparse.ArgumentParser(add_help=False)
    _add_check_toggle_args(toggles)
    parser = argparse.ArgumentParser(
        prog=prog or TOOL_CHECKER,
        description=(
            "Compare ISO 19650 drawing filenames with title-block contents. "
            "With no arguments, checks every PDF in the folder that contains this program."
        ),
        parents=[toggles],
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
            f"from the title block ({TOOL_RENAMER}). No prompt."
        ),
    )
    parser.add_argument(
        "--document-list",
        type=Path,
        default=None,
        help="Client portal document-list Excel/CSV (otherwise scanned in the folder)",
    )
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser(
        "check",
        help="Scan PDFs and write an Excel QA report",
        parents=[toggles],
    )
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
        help="Excel report path (default: {project}_{ddmmyy}.xlsx in the target folder)",
    )
    check.add_argument(
        "--recursive",
        action="store_true",
        help="Include PDFs in subfolders",
    )
    check.add_argument(
        "--document-list",
        type=Path,
        default=None,
        help="Client portal document-list Excel/CSV (otherwise scanned in the folder)",
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
    portal = next((item.portal_list_name for item in results if item.portal_list_name), "")
    if portal:
        print(f"  Portal document list: {portal}")


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


@dataclass
class DroppedSelection:
    pdfs: list[Path] = field(default_factory=list)
    dwgs: list[Path] = field(default_factory=list)
    document_list: Path | None = None
    ignored: list[Path] = field(default_factory=list)

    @property
    def has_drawings(self) -> bool:
        return bool(self.pdfs or self.dwgs)


def _is_pdf(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".pdf"


def _is_dwg(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".dwg"


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path.resolve()).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _working_folder(pdfs: list[Path], fallback: Path) -> Path:
    parents = {path.resolve().parent for path in pdfs}
    if len(parents) == 1:
        return next(iter(parents))
    return fallback


def _take_dropped_inputs(argv: list[str]) -> tuple[list[str], DroppedSelection]:
    """Pull dragged-and-dropped files out of argv before argparse.

    Windows passes every dropped path as an argument. That is not a subcommand,
    so argparse would otherwise reject PDFs, DWGs, and spreadsheets.
    """
    dropped = DroppedSelection()
    if not argv or argv[0] in {"check", "inspect"}:
        return argv, dropped
    remaining: list[str] = []
    skip_next = False
    for item in argv:
        if skip_next:
            remaining.append(item)
            skip_next = False
            continue
        flag = item.split("=", 1)[0]
        if flag in _TOGGLE_VALUE_FLAGS and "=" not in item:
            remaining.append(item)
            skip_next = True
            continue
        candidate = Path(item)
        if is_spreadsheet(candidate):
            if dropped.document_list is None:
                dropped.document_list = candidate
            else:
                dropped.ignored.append(candidate)
            continue
        if _is_pdf(candidate):
            dropped.pdfs.append(candidate)
            continue
        if _is_dwg(candidate):
            dropped.dwgs.append(candidate)
            continue
        if candidate.is_dir():
            dropped.pdfs.extend(
                path for path in candidate.iterdir() if _is_pdf(path)
            )
            dropped.dwgs.extend(
                path for path in candidate.iterdir() if _is_dwg(path)
            )
            continue
        if candidate.exists():
            dropped.ignored.append(candidate)
            continue
        remaining.append(item)
    dropped.pdfs = _unique_paths(dropped.pdfs)
    dropped.dwgs = _unique_paths(dropped.dwgs)
    return remaining, dropped


def _print_report_paths(saved: Path) -> None:
    print(f"Report: {saved}")
    designer = designer_report_path(saved)
    if designer.is_file():
        print(f"Designer: {designer}")
    designer_text = designer_text_report_path(saved)
    if designer_text.is_file():
        print(f"Designer comments: {designer_text}")
    control = document_control_report_path(saved)
    if control.is_file():
        print(f"Document control: {control}")


def _cli_check_flags_used(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "checks", None)
        or getattr(args, "disable", None)
        or getattr(args, "enable", None)
    )


def _should_prompt_checks(args: argparse.Namespace) -> bool:
    if getattr(args, "list_checks", False):
        return False
    if getattr(args, "prompt_checks", False):
        return True
    if not getattr(args, "custom_checks", False):
        return False
    if getattr(args, "no_pause", False):
        return False
    if _cli_check_flags_used(args):
        return False
    return True


def _toggle_change_lines(before: CheckOptions, after: CheckOptions, names: list[str]) -> list[str]:
    """Short ON/OFF lines for the checks the user just typed."""
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    turned_off: list[str] = []
    turned_on: list[str] = []
    for name in seen:
        if name == "previews":
            if before.field_previews and not after.field_previews:
                turned_off.append(name)
            elif not before.field_previews and after.field_previews:
                turned_on.append(name)
            continue
        if before.allows(name) and not after.allows(name):
            turned_off.append(name)
        elif not before.allows(name) and after.allows(name):
            turned_on.append(name)
    lines: list[str] = []
    if turned_off:
        lines.append("Turned OFF: " + ", ".join(turned_off))
    if turned_on:
        lines.append("Turned ON:  " + ", ".join(turned_on))
    return lines


def _prompt_check_toggles(initial: CheckOptions | None = None) -> CheckOptions:
    start = initial or CheckOptions()
    current = CheckOptions(frozenset(start.enabled), field_previews=start.field_previews)
    print()
    print(format_check_menu(current))
    print()
    while True:
        try:
            raw = input("Toggle (Enter to run with the settings above): ").strip()
        except EOFError:
            raw = ""
        if not raw:
            return current
        try:
            names = parse_check_choice(raw)
        except UnknownCheckError as exc:
            print(f"  {exc}")
            continue
        updated = apply_check_toggles(current, names)
        print()
        for line in _toggle_change_lines(current, updated, names):
            print("  " + line)
        current = updated
        print()
        print(format_check_menu(current))
        print()


def _check_options_from_args(args: argparse.Namespace) -> CheckOptions:
    options = resolve_check_options(
        only=getattr(args, "checks", None),
        disable=getattr(args, "disable", None),
        enable=getattr(args, "enable", None),
    )
    if getattr(args, "previews", False):
        options.field_previews = True
    return options


def _print_tool_banner(
    *,
    standardize_names: bool,
    custom_mode: bool,
    check_options,
) -> None:
    if standardize_names:
        print(f"{tool_banner(TOOL_RENAMER)} - Title-block QA + standardize filenames")
    elif custom_mode:
        print(f"{tool_banner(TOOL_CUSTOM)} - Title-block QA (menu, or --disable / --checks)")
    else:
        print(f"{tool_banner(TOOL_CHECKER)} - Title-block QA")
    if custom_mode or (check_options and check_options.disabled_ids()):
        disabled = check_options.disabled_ids() if check_options else []
        if disabled:
            print("Disabled checks: " + ", ".join(disabled))
        elif custom_mode:
            print("Checks: all on.  --disable portal-revision   --list-checks")
    if check_options and check_options.field_previews:
        print("Field previews: on (every drawing)")


def run_folder_check(
    folder: Path,
    *,
    config_dir: Path | None = None,
    output: Path | None = None,
    recursive: bool = False,
    progress: bool = True,
    standardize_names: bool = False,
    document_list: Path | None = None,
    check_options=None,
    custom_mode: bool = False,
    prompt_checks: bool = False,
    pdfs: list[Path] | None = None,
    extra_dwgs: list[Path] | None = None,
) -> int:
    folder = folder.resolve()
    config_path = resolve_config_dir(folder, config_dir)
    print("=" * 60)
    _print_tool_banner(
        standardize_names=standardize_names,
        custom_mode=custom_mode,
        check_options=check_options,
    )
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
    if check_options is not None:
        config.check_options = check_options
    if prompt_checks:
        check_options = _prompt_check_toggles(check_options)
        config.check_options = check_options
        disabled = check_options.disabled_ids()
        print("Disabled checks: " + (", ".join(disabled) if disabled else "none"))
        if check_options.field_previews:
            print("Field previews: on (every drawing)")
        print()

    selected = pdfs is not None
    if pdfs is None:
        pdfs = iter_pdfs(folder, recursive=recursive)
    else:
        pdfs = [path.resolve() for path in pdfs if _is_pdf(path)]
    if not pdfs:
        if selected:
            print("No PDF files in the dropped selection.")
        else:
            print("No PDF files found in this folder.")
        return 2

    if selected:
        print(f"Selected {len(pdfs)} PDF(s)")
    else:
        print(f"Found {len(pdfs)} PDF(s)")
    if extra_dwgs:
        print(f"Dropped DWG(s): {len(extra_dwgs)} (used for pairing)")
    print()

    def on_pdf(index: int, total: int, result) -> None:
        if progress:
            print(f"[{index}/{total}] {result.path.name} ...", flush=True)
            print(f"         {result.status.value}")

    results = check_paths(
        pdfs,
        config,
        standardize=standardize_names,
        on_pdf=on_pdf,
        document_list=document_list,
        extra_dwgs=extra_dwgs,
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

    report_path = output if output is not None else default_report_path(folder, results)
    saved = write_report(results, report_path)
    _print_summary(results)
    if document_list is not None and not any(item.portal_list_name for item in results):
        print(
            f"  Portal document list not used: could not read Doc Ref / Revision "
            f"columns from {document_list.name}"
        )
    _print_report_paths(saved)
    if timing_enabled():
        print()
        print(format_timing_report())
    
    problems = sum(1 for item in results if item.status.value != "MATCH")
    return 1 if problems else 0


def cmd_check(args: argparse.Namespace) -> int:
    standardize_names = getattr(args, "standardize_names", False)
    document_list = getattr(args, "document_list", None)
    check_options = _check_options_from_args(args)
    custom_mode = bool(getattr(args, "custom_checks", False))
    prompt_checks = _should_prompt_checks(args)
    target = args.input.resolve() if args.input is not None else app_dir()
    if target.is_file() and is_spreadsheet(target):
        return run_folder_check(
            target.parent,
            config_dir=args.config_dir,
            output=args.output,
            recursive=args.recursive,
            progress=True,
            standardize_names=standardize_names,
            document_list=target,
            check_options=check_options,
            custom_mode=custom_mode,
            prompt_checks=prompt_checks,
        )
    if target.is_file():
        if prompt_checks:
            check_options = _prompt_check_toggles(check_options)
        config = load_config(resolve_config_dir(target.parent, args.config_dir))
        config.check_options = check_options
        pdfs = iter_pdfs(target)
        results = check_paths(
            pdfs, config, standardize=standardize_names, document_list=document_list
        )
        if standardize_names:
            print("Renaming file to document-reference_title_revision...")
            stats = apply_renames(results)
            _print_rename_stats(stats)
        output = args.output or default_report_path(target.parent, results)
        saved = write_report(results, output)
        _print_summary(results)
        _print_report_paths(saved)
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
        document_list=document_list,
        check_options=check_options,
        custom_mode=custom_mode,
        prompt_checks=prompt_checks,
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

    custom = "--custom-checks" in cleaned
    parser = build_parser(prog=TOOL_CUSTOM if custom else TOOL_CHECKER)
    cleaned, dropped = _take_dropped_inputs(cleaned)
    args = parser.parse_args(cleaned)
    if dropped.document_list is not None and getattr(args, "document_list", None) is None:
        args.document_list = dropped.document_list
    if pause_flag is False:
        args.no_pause = True
        args.pause = False
    elif pause_flag is True:
        args.pause = True
        args.no_pause = False
    
    code = 0
    try:
        if getattr(args, "list_checks", False):
            print(format_check_list())
            code = 0
        elif args.command is None:
            if dropped.ignored:
                print("Ignored (not a PDF, DWG, or portal list):")
                for path in dropped.ignored:
                    print(f"  {path.name}")
                print()
            folder = app_dir()
            selected_pdfs = None
            extra_dwgs = None
            if dropped.has_drawings:
                folder = _working_folder(dropped.pdfs, app_dir())
                selected_pdfs = dropped.pdfs
                extra_dwgs = dropped.dwgs or None
            code = run_folder_check(
                folder,
                standardize_names=getattr(args, "standardize_names", False),
                document_list=getattr(args, "document_list", None),
                check_options=_check_options_from_args(args),
                custom_mode=bool(getattr(args, "custom_checks", False)),
                prompt_checks=_should_prompt_checks(args),
                pdfs=selected_pdfs,
                extra_dwgs=extra_dwgs,
            )
        elif args.command == "check":
            code = cmd_check(args)
        elif args.command == "inspect":
            code = cmd_inspect(args)
        else:
            parser.error(f"Unknown command {args.command}")
            code = 2
    except UnknownCheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        code = 2
    except Exception as exc:  # noqa: BLE001 - keep the console open on unexpected errors
        print(f"ERROR: {exc}", file=sys.stderr)
        code = 2
    if _should_pause(args):
        _pause()
    return code
