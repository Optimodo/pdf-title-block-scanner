from pathlib import Path

from drawing_qa.checker import check_pdf
from drawing_qa.client import client_is_allowed, format_allowed_clients
from drawing_qa.compare import build_result
from drawing_qa.config_loader import ClientCheckConfig, load_config
from drawing_qa.designer_brief import designer_actions
from drawing_qa.models import CheckStatus, DocumentResult, FilenameFields, TitleBlockFields
from tests.pdf_fixtures import write_bottom_right_pdf

COMPARE_RULES = {
    "document_reference": "required",
    "revision": "if_both_present",
    "title": "if_both_present",
    "suitability": "if_both_present",
    "date": "if_both_present",
}


def test_client_matching_accepts_shorter_and_ampersand_forms():
    oval = ["Berkeley", "Berkeley Homes"]
    assert client_is_allowed("Berkeley Homes", oval)
    assert client_is_allowed("berkeley", oval)
    assert client_is_allowed("Berkeley Homes plc", oval)
    assert not client_is_allowed("Seven Capital Woodrow", oval)
    assert client_is_allowed("L&Q", ["L&Q"])
    assert client_is_allowed("L & Q", ["L&Q"])
    assert client_is_allowed("MEP", ["MEP", "MBS", "L&Q"])
    assert not client_is_allowed("TEMP", ["MEP"])
    assert format_allowed_clients(["Berkeley", "Berkeley Homes"]) == (
        "Berkeley or Berkeley Homes"
    )


def test_wcr_accepts_seven_capital_woodrow(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "WCR-MBS-B7-XX-DR-M-5301-C01.pdf",
        document_reference="WCR-MBS-B7-XX-DR-M-5301",
        title="Mechanical Services Layout",
        revision="C01",
        suitability="A - Construction",
        client="Seven Capital Woodrow",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.client == "Seven Capital Woodrow"
    assert CheckStatus.CLIENT_ERROR not in result.issues


def test_oval_accepts_berkeley_homes_on_mbs_right(tmp_path: Path, config_dir: Path):
    from tests.pdf_fixtures import write_mbs_right_pdf

    pdf = write_mbs_right_pdf(
        tmp_path / "R459-MBS-DZ-BA-DR-W-55100-P01.pdf",
        document_reference="R459-MBS-DZ-BA-DR-W-55100",
        title="Sprinkler layout",
        revision="P01",
        suitability="S3",
        client="Berkeley Homes",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.client == "Berkeley Homes"
    assert CheckStatus.CLIENT_ERROR not in result.issues


def test_wrong_client_is_flagged(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "WCR-MBS-B7-XX-DR-M-5301-C01.pdf",
        document_reference="WCR-MBS-B7-XX-DR-M-5301",
        title="Mechanical Services Layout",
        revision="C01",
        suitability="A - Construction",
        client="Berkeley Homes",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.CLIENT_ERROR in result.issues
    assert "Seven Capital Woodrow" in " ".join(result.notes)
    text = designer_actions(result)
    assert "client" in text.lower()
    assert "Seven Capital Woodrow" in text
    assert "Berkeley Homes" in text


def test_missing_client_is_flagged_for_configured_project(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "HPA-MBS-D3-LG-DR-X-55103-P01.pdf",
        document_reference="HPA-MBS-D3-LG-DR-X-55103",
        title="Lighting layout",
        revision="P01",
        suitability="S3 - For Review & Comment",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.CLIENT_ERROR in result.issues
    text = designer_actions(result)
    assert "Add the client name" in text
    assert "London Square" in text


def test_hpa_accepts_london_square(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "HPA-MBS-D3-LG-DR-X-55103-P01.pdf",
        document_reference="HPA-MBS-D3-LG-DR-X-55103",
        title="Lighting layout",
        revision="P01",
        suitability="S3 - For Review & Comment",
        client="London Square",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.titleblock.client == "London Square"
    assert CheckStatus.CLIENT_ERROR not in result.issues


def test_barking_accepts_mbs_and_lq(tmp_path: Path, config_dir: Path):
    for name in ("MBS", "L&Q"):
        pdf = write_bottom_right_pdf(
            tmp_path / f"J106309-MEP-02-ZZ-DR-X-600026-{name.replace('&', '')}-C01.pdf",
            document_reference="J106309-MEP-02-ZZ-DR-X-600026",
            title="Ground Floor GA",
            revision="C01",
            suitability="S4 - Suitable for Other Stage Approvals",
            client=name,
        )
        result = check_pdf(pdf, load_config(config_dir))
        assert result.titleblock.client == name
        assert CheckStatus.CLIENT_ERROR not in result.issues


def test_unlisted_project_is_not_checked_for_client(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
        suitability="S3 - Review and comment",
        client="Anyone",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.CLIENT_ERROR not in result.issues
    assert result.status == CheckStatus.MATCH


def test_client_check_can_be_disabled():
    result = DocumentResult(
        path=Path("WCR-MBS-B7-XX-DR-M-5301-C01.pdf"),
        filename=FilenameFields(
            raw_stem="WCR-MBS-B7-XX-DR-M-5301-C01",
            document_reference="WCR-MBS-B7-XX-DR-M-5301",
            revision="C01",
            parse_ok=True,
            parts={"project": "WCR"},
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="WCR-MBS-B7-XX-DR-M-5301",
            revision="C01",
            title="Mechanical Services Layout",
            suitability="A - Construction",
            client="Wrong",
        ),
    )
    result = build_result(
        result,
        COMPARE_RULES,
        client_check_config=ClientCheckConfig(
            enabled=False,
            projects={"WCR": ["Seven Capital Woodrow"]},
        ),
    )
    assert CheckStatus.CLIENT_ERROR not in result.issues
