from __future__ import annotations

from pathlib import Path

from drawing_qa.checks import CheckOptions
from drawing_qa.compare import build_result
from drawing_qa.config_loader import AppConfig
from drawing_qa.detect import extract_titleblock
from drawing_qa.document_list import (
    check_document_list,
    find_document_list,
    load_document_list,
)
from drawing_qa.dwg_pairing import check_dwg_pairing
from drawing_qa.extract import clear_page_word_cache, require_pymupdf
from drawing_qa.filename import parse_filename
from drawing_qa.models import CheckStatus, DocumentResult, TitleBlockFields, finalize_status
from drawing_qa.preview import render_preview
from drawing_qa.timing import span as timing_span
from drawing_qa.validation import (
    check_date_regression,
    check_duplicates,
    standardize_filename,
    suggest_filename,
)


def iter_pdfs(input_path: Path, *, recursive: bool = False) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF: {input_path}")
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(input_path)
    iterator = input_path.rglob("*") if recursive else input_path.iterdir()
    return sorted(
        p
        for p in iterator
        if p.is_file() and p.suffix.lower() == ".pdf"
    )


def check_pdf(path: Path, config: AppConfig) -> DocumentResult:
    filename = parse_filename(
        path,
        field_count=config.field_count,
        revision_pattern=config.revision_pattern,
    )
    result = DocumentResult(
        path=path,
        filename=filename,
        titleblock=TitleBlockFields(),
        original_filename=path.name,
    )
    page = None
    try:
        require_pymupdf()
        import pymupdf

        with timing_span("open_pdf"):
            doc = pymupdf.open(path)
        try:
            result.page_count = doc.page_count
            if doc.page_count < 1:
                result.status = CheckStatus.ERROR
                result.error = "PDF has no pages"
                return result
            page = doc[0]
            with timing_span("extract_titleblock"):
                result.titleblock = extract_titleblock(
                    page,
                    config.layouts,
                    config.min_layout_score,
                )
            # Compare while the page is still open so previews can render.
            with timing_span("compare"):
                result = build_result(
                    result,
                    config.compare_rules,
                    config.spell_check,
                    config.suitability_check,
                    config.client_check,
                    check_options=config.check_options,
                )
            if (config.preview and config.preview.all_files) or result.status != CheckStatus.MATCH:
                with timing_span("preview"):
                    result.preview_png = render_preview(page, result.titleblock)
        finally:
            if page is not None:
                clear_page_word_cache(page)
            doc.close()
    except Exception as exc:  # noqa: BLE001 - surface any PDF read failure in the report
        clear_page_word_cache(page)
        result.status = CheckStatus.ERROR
        result.error = str(exc)
        result.filename = filename
        return result
    return result


def _fill_missing_previews(results: list[DocumentResult], config: AppConfig) -> None:
    """Render crops for rows that only became review after folder-level checks."""
    all_files = bool(config.preview and config.preview.all_files)
    for result in results:
        if result.preview_png or result.status == CheckStatus.ERROR:
            continue
        if result.status == CheckStatus.MATCH and not all_files:
            continue
        page = None
        try:
            require_pymupdf()
            import pymupdf

            doc = pymupdf.open(result.path)
            try:
                if doc.page_count < 1:
                    continue
                page = doc[0]
                with timing_span("preview"):
                    result.preview_png = render_preview(page, result.titleblock)
            finally:
                if page is not None:
                    clear_page_word_cache(page)
                doc.close()
        except Exception:  # noqa: BLE001 - report can still ship without a crop
            clear_page_word_cache(page)


def check_paths(
    paths: list[Path],
    config: AppConfig,
    *,
    standardize: bool = False,
    on_pdf=None,
    document_list: Path | None = None,
) -> list[DocumentResult]:
    results: list[DocumentResult] = []
    total = len(paths)
    for index, path in enumerate(paths, start=1):
        with timing_span("check_pdf"):
            result = check_pdf(path, config)
        results.append(result)
        if on_pdf is not None:
            on_pdf(index, total, result)

    if results:
        folder = results[0].path.parent
        with timing_span("validations"):
            options = config.check_options or CheckOptions()
            if options.allows("duplicates"):
                results = check_duplicates(results)
            if options.allows("date-regression"):
                results = check_date_regression(results)
            results = check_dwg_pairing(
                results, folder, flag_issues=options.allows("dwg")
            )
            list_cfg = config.document_list
            want_portal = options.allows("portal-revision") or options.allows(
                "portal-title"
            )
            if list_cfg and list_cfg.enabled and list_cfg.layout and want_portal:
                project_codes = sorted(
                    {
                        (item.filename.parts.get("project") or "").strip().upper()
                        for item in results
                        if item.filename.parts.get("project")
                    }
                )
                list_path = find_document_list(
                    folder,
                    list_cfg.layout,
                    explicit=document_list,
                    project_codes=project_codes,
                )
                if list_path is not None:
                    try:
                        index = load_document_list(list_path, list_cfg.layout)
                    except Exception:  # noqa: BLE001 - optional check must not abort QA
                        index = None
                    if index is not None and index.by_ref:
                        results = check_document_list(
                            results, index, list_cfg.layout, check_options=options
                        )

            for result in results:
                finalize_status(result)
                if not result.original_filename:
                    result.original_filename = result.path.name
                if standardize:
                    result.suggested_filename = standardize_filename(result)
                else:
                    result.suggested_filename = suggest_filename(result)

            _fill_missing_previews(results, config)

    return results
