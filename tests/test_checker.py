from pathlib import Path

from drawing_qa.checker import check_pdf, check_paths
from drawing_qa.config_loader import load_config
from drawing_qa.models import CheckStatus
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
    assert set(wb.sheetnames) == {"Summary", "All documents", "Needs attention", "Matches"}
    assert wb["All documents"].max_row == 3  # header + 2 rows
    assert wb["Matches"].max_row == 2
    assert wb["Needs attention"].max_row == 2
