from datetime import datetime
from pathlib import Path

from drawing_qa.models import CheckStatus, Confidence, DocumentResult, FilenameFields, TitleBlockFields
from drawing_qa.paths import designer_report_path
from drawing_qa.report import DESIGNER_HEADER_ROW, report_project_label, report_stem, write_report


def _result(*, project: str, name: str = "", confidence: Confidence = Confidence.HIGH) -> DocumentResult:
    return DocumentResult(
        path=Path(f"{project}-WXY-ZZ-00-DR-A-0001-P01.pdf"),
        filename=FilenameFields(
            raw_stem=f"{project}-WXY-ZZ-00-DR-A-0001-P01",
            document_reference=f"{project}-WXY-ZZ-00-DR-A-0001",
            revision="P01",
            parse_ok=True,
            parts={"project": project},
        ),
        titleblock=TitleBlockFields(
            document_reference=f"{project}-WXY-ZZ-00-DR-A-0001",
            title="Ground Floor GA",
            revision="P01",
        ),
        status=CheckStatus.MATCH if confidence == Confidence.HIGH else CheckStatus.MISMATCH,
        confidence=confidence,
        purpose_list_name=name,
    )


def test_report_label_prefers_whitelist_name():
    assert report_project_label([_result(project="R459", name="Oval C+D")]) == "Oval C+D"


def test_report_label_falls_back_to_project_code():
    assert report_project_label([_result(project="ABC")]) == "ABC"


def test_report_label_joins_distinct_projects():
    results = [
        _result(project="R459", name="Oval C+D"),
        _result(project="J106309", name="Barking Riverside"),
    ]
    assert report_project_label(results) == "Oval C+D, Barking Riverside"


def test_report_stem_uses_ddmmyy():
    when = datetime(2026, 8, 26, 9, 0)
    assert report_stem([_result(project="R459", name="Oval C+D")], when=when) == "Oval C+D_260826"
    assert report_stem([_result(project="ABC")], when=when) == "ABC_260826"


def test_write_report_also_writes_designer_sidecar(tmp_path: Path):
    result = _result(project="R459", name="Oval C+D", confidence=Confidence.REVIEW)
    result.issues = [CheckStatus.MISMATCH]
    output = write_report([result], tmp_path / "full.xlsx")
    side = designer_report_path(output)
    assert side.is_file()
    from openpyxl import load_workbook

    main = load_workbook(output)
    assert main.sheetnames[0] == "Summary"
    assert "Designer actions" in main.sheetnames
    designer = load_workbook(side)
    assert designer.sheetnames == ["Designer actions"]
    sheet = designer.active
    assert sheet["A1"].value == "Designer actions — Oval C+D"
    assert sheet["B4"].value == 1
    assert sheet["B5"].value == 1
    assert sheet["B6"].value == 0
    assert sheet.cell(DESIGNER_HEADER_ROW, 1).value == "Drawing number"
    assert sheet.cell(DESIGNER_HEADER_ROW + 1, 1).value == "R459-WXY-ZZ-00-DR-A-0001"
    assert main["Designer actions"]["A1"].value == sheet["A1"].value
