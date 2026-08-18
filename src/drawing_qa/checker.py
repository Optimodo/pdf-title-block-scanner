from __future__ import annotations

from pathlib import Path

from drawing_qa.compare import build_result
from drawing_qa.config_loader import AppConfig
from drawing_qa.detect import extract_titleblock
from drawing_qa.extract import require_pymupdf
from drawing_qa.filename import parse_filename
from drawing_qa.models import CheckStatus, DocumentResult, TitleBlockFields


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
    )
    try:
        require_pymupdf()
        import pymupdf

        with pymupdf.open(path) as doc:
            result.page_count = doc.page_count
            if doc.page_count < 1:
                result.status = CheckStatus.ERROR
                result.error = "PDF has no pages"
                return result
            page = doc[0]
            result.titleblock = extract_titleblock(
                page,
                config.layouts,
                config.min_layout_score,
            )
    except Exception as exc:  # noqa: BLE001 - surface any PDF read failure in the report
        result.status = CheckStatus.ERROR
        result.error = str(exc)
        result.filename = filename
        return result
    return build_result(result, config.compare_rules)


def check_paths(paths: list[Path], config: AppConfig) -> list[DocumentResult]:
    return [check_pdf(path, config) for path in paths]
