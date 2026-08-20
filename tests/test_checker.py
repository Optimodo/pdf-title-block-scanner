from pathlib import Path

from drawing_qa.checker import check_pdf, check_paths, iter_pdfs
from drawing_qa.config_loader import load_config
from drawing_qa.models import CheckStatus, Confidence
from drawing_qa.report import write_report
from tests.pdf_fixtures import (
    write_bottom_right_pdf,
    write_bottom_strip_pdf,
    write_mbs_right_pdf,
    write_plain_pdf,
)


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


def test_filename_without_revision_or_title_can_still_match(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.filename.revision is None
    assert result.filename.title is None
    assert result.status == CheckStatus.MATCH
    assert result.confidence == Confidence.HIGH


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
    data = wb["All documents"]
    assert data["F1"].value == "Filename title"
    assert data["J1"].value == "Status / suitability"
    assert data.column_dimensions["C"].width == 35
    assert data.column_dimensions["D"].width == 35
    assert data.column_dimensions["E"].width == 35
    assert data.column_dimensions["F"].width == 35
    assert data.column_dimensions["G"].width == 35
    assert data.column_dimensions["J"].width == 25
    assert data.column_dimensions["L"].width == 40
    # Column O is New filename (45); Rename result is P; Notes moved to R (60)
    assert data["O1"].value == "New filename"
    assert data["P1"].value == "Rename result"
    assert data.column_dimensions["O"].width == 45
    assert data.column_dimensions["R"].width == 60
    assert data["A1"].font.size == 10
    assert data["C2"].font.size == 10
    assert data["A1"].alignment.horizontal == "center"
    assert data["O1"].alignment.horizontal == "center"


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


def test_detects_mbs_right_title_block(tmp_path: Path, config_dir: Path):
    pdf = write_mbs_right_pdf(
        tmp_path / "R459-MBS-DZ-BA-DR-W-55100-P01.pdf",
        document_reference="R459-MBS-DZ-BA-DR-W-55100",
        title="Block D Commercial Sprinkler layout Level LG\nSheet 1 of 4",
        revision="P01",
        suitability="S3",
        date="14.08.26",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.layout_id == "mbs_right"
    assert result.titleblock.document_reference == "R459-MBS-DZ-BA-DR-W-55100"
    assert result.titleblock.revision == "P01"
    assert result.titleblock.title == "Block D Commercial Sprinkler layout Level LG Sheet 1 of 4"
    assert result.titleblock.suitability == "S3 - REVIEW & COMMENT"
    assert result.titleblock.date == "14.08.26"
    assert result.titleblock.history.latest is not None
    assert result.titleblock.history.latest.revision == "P01"
    assert result.status == CheckStatus.MATCH


def test_real_mbs_drawing_if_present(config_dir: Path):
    sample = Path("test files") / "R459-MBS-DZ-BA-DR-W-55100.pdf"
    if not sample.is_file():
        return
    result = check_pdf(sample, load_config(config_dir))
    assert result.titleblock.layout_id == "mbs_right"
    assert result.titleblock.document_reference == "R459-MBS-DZ-BA-DR-W-55100"
    assert result.titleblock.revision == "P01"
    assert result.titleblock.date == "14.08.26"
    assert result.titleblock.suitability and result.titleblock.suitability.startswith("S3")
    assert result.titleblock.title and "Sprinkler" in result.titleblock.title
    assert result.titleblock.history.latest is not None
    assert result.titleblock.history.latest.revision == "P01"
    assert result.status == CheckStatus.MATCH
    assert result.confidence == Confidence.HIGH


def test_real_multiline_title_and_suitability_if_present(config_dir: Path):
    sample = Path("test files") / "J106309-MEP-02-ZZ-DR-X-600026.pdf"
    if not sample.is_file():
        return
    result = check_pdf(sample, load_config(config_dir))
    assert result.titleblock.title == "Electrical Layout - Apartment Type Z2 - L"
    assert result.titleblock.suitability == "S2 - Suitable For Tender"


def test_real_wcr_construction_status_and_date_if_present(config_dir: Path):
    sample = Path("test files") / (
        "WCR-MBS-B7-XX-DR-M-5301 - B7 - Mechanical Services Layout"
        " - Below Level 00 - Sheet 01 of 03_C01.pdf"
    )
    if not sample.is_file():
        return
    result = check_pdf(sample, load_config(config_dir))
    assert result.filename.title and result.filename.title.startswith("B7")
    assert result.titleblock.suitability == "A - CONSTRUCTION"
    assert result.titleblock.date == "01.06.2026"
    assert result.titleblock.history.latest is not None
    assert result.titleblock.history.latest.revision == "C01"
    assert "Current date taken from latest history row" not in result.notes


def test_real_hpa_history_rows_if_present(config_dir: Path):
    sample = Path("test files") / "HPA-MBS-D3-LG-DR-X-55103-C02.pdf"
    if not sample.is_file():
        return
    result = check_pdf(sample, load_config(config_dir))
    assert result.titleblock.history.latest is not None
    assert result.titleblock.history.latest.revision == "C02"
    assert len(result.titleblock.history.rows) >= 4


def test_iter_pdfs_is_not_recursive(tmp_path: Path):
    write_plain_pdf(tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf")
    nested = tmp_path / "nested"
    write_plain_pdf(nested / "ABC-WXY-ZZ-00-DR-A-0002-P01.pdf")
    found = iter_pdfs(tmp_path, recursive=False)
    assert [p.name for p in found] == ["ABC-WXY-ZZ-00-DR-A-0001-P01.pdf"]
    found_all = iter_pdfs(tmp_path, recursive=True)
    assert len(found_all) == 2
