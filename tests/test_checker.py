from pathlib import Path

from drawing_qa.checker import check_pdf, check_paths, iter_pdfs
from drawing_qa.config_loader import load_config
from drawing_qa.models import CheckStatus, Confidence
from drawing_qa.report import write_report
from tests.pdf_fixtures import write_bottom_right_pdf, write_bottom_strip_pdf, write_plain_pdf


def test_detects_bottom_right_and_matches(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.layout_id == "bottom_right"
    assert result.titleblock.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert result.titleblock.revision == "P01"
    assert result.titleblock.title == "Ground Floor GA"
    assert result.status == CheckStatus.MATCH


def test_detects_bottom_strip_layout(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_strip_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0102-C02.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0102",
        title="Roof Plan",
        revision="C02",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.layout_id == "bottom_strip"
    assert result.status == CheckStatus.MATCH
    assert result.titleblock.title == "Roof Plan"


def test_reports_revision_mismatch(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P03",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.status == CheckStatus.MISMATCH
    revision = next(item for item in result.comparisons if item.name == "revision")
    assert revision.matched is False


def test_undetected_when_no_title_block(tmp_path: Path, config_dir: Path):
    pdf = write_plain_pdf(tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf")
    result = check_pdf(pdf, load_config(config_dir))
    assert result.status == CheckStatus.UNDETECTED


def test_filename_parse_error(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "A-101.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Plan",
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.status == CheckStatus.FILENAME_PARSE_ERROR
    assert result.titleblock.layout_id == "bottom_right"
    assert result.titleblock.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert result.titleblock.revision == "P01"
    assert result.titleblock.title == "Plan"
    assert result.filename.document_reference is None


def test_excel_report_created(tmp_path: Path, config_dir: Path):
    match_pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    mismatch_pdf = write_bottom_strip_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0102-C01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0102",
        title="Roof Plan",
        revision="C02",
    )
    results = check_paths([match_pdf, mismatch_pdf], load_config(config_dir))
    output = write_report(results, tmp_path / "report.xlsx")
    assert output.is_file()
    from openpyxl import load_workbook

    wb = load_workbook(output)
    assert set(wb.sheetnames) == {"Summary", "Review needed", "High confidence", "All documents"}
    assert wb["All documents"].max_row == 3  # header + 2 rows
    assert wb["High confidence"].max_row == 2
    assert wb["Review needed"].max_row == 2
    assert wb["All documents"]._images


def test_history_latest_used_not_older_rows(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P03.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P03",
        date="15.06.24",
        suitability="S4",
        history=[
            ("P01", "12.01.24", "First issue"),
            ("P02", "03.03.24", "Updated for comment"),
            ("P03", "15.06.24", "S4 Construction"),
        ],
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.revision == "P03"
    assert result.titleblock.date == "15.06.24"
    assert result.titleblock.history.latest is not None
    assert result.titleblock.history.latest.revision == "P03"
    assert result.status == CheckStatus.MATCH
    assert result.confidence == Confidence.HIGH
    assert result.preview_png


def test_history_mismatch_against_current_rev(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P03.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P03",
        date="15.06.24",
        suitability="S4",
        history=[
            ("P01", "12.01.24", "First issue"),
            ("P02", "03.03.24", "Updated for comment"),
        ],
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.revision == "P03"
    assert result.titleblock.history.latest is not None
    assert result.titleblock.history.latest.revision == "P02"
    assert result.status == CheckStatus.HISTORY_MISMATCH
    assert result.confidence == Confidence.REVIEW


def test_iter_pdfs_is_not_recursive(tmp_path: Path):
    write_plain_pdf(tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf")
    nested = tmp_path / "nested"
    write_plain_pdf(nested / "ABC-WXY-ZZ-00-DR-A-0002-P01.pdf")
    found = iter_pdfs(tmp_path, recursive=False)
    assert [p.name for p in found] == ["ABC-WXY-ZZ-00-DR-A-0001-P01.pdf"]
    found_all = iter_pdfs(tmp_path, recursive=True)
    assert len(found_all) == 2
