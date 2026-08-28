from pathlib import Path

from drawing_qa.checker import check_pdf
from drawing_qa.compare import build_result
from drawing_qa.config_loader import SuitabilityCheckConfig, load_config
from drawing_qa.models import CheckStatus, DocumentResult, FilenameFields, TitleBlockFields
from drawing_qa.suitability import (
    allowed_values_for_project,
    normalize_suitability,
    revision_purpose_mismatch_note,
    suitability_is_allowed,
    suitability_purpose_family,
)
from tests.pdf_fixtures import write_bottom_right_pdf

ISO_LIST = [
    "S3 - Suitable for review and comment",
    "S3 - Review and comment",
    "S3 - Review & Comment",
    "A1 - Authorised and accepted",
]


def _matching_result(suitability: str) -> DocumentResult:
    return DocumentResult(
        path=Path("ABC-WXY-ZZ-00-DR-A-0001-P01.pdf"),
        filename=FilenameFields(
            raw_stem="ABC-WXY-ZZ-00-DR-A-0001-P01",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="P01",
            parse_ok=True,
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="P01",
            title="Ground Floor GA",
            suitability=suitability,
        ),
    )


def test_ampersand_matches_and():
    assert normalize_suitability("S3 - Review & Comment") == normalize_suitability(
        "S3 - Review and comment"
    )
    assert suitability_is_allowed("S3 - REVIEW & COMMENT", ISO_LIST)


def test_known_code_with_typo_description_is_rejected():
    assert not suitability_is_allowed("S3 - Reveu and comment", ISO_LIST)


def test_unknown_combination_is_rejected():
    assert not suitability_is_allowed("S9 - Made up status", ISO_LIST)


def test_code_only_accepted_when_code_is_on_whitelist():
    assert suitability_is_allowed("S3", ISO_LIST, accept_code_only=True)
    assert not suitability_is_allowed("S3", ISO_LIST, accept_code_only=False)


def test_code_only_rejected_when_code_not_on_whitelist():
    assert not suitability_is_allowed("S9", ISO_LIST, accept_code_only=True)


def test_build_result_flags_unknown_suitability():
    result = build_result(
        _matching_result("S3 - Reveu and comment"),
        {
            "document_reference": "required",
            "revision": "if_both_present",
            "title": "if_both_present",
            "suitability": "if_both_present",
            "date": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(values=ISO_LIST),
    )
    assert result.status == CheckStatus.SUITABILITY_ERROR
    assert CheckStatus.SUITABILITY_ERROR in result.issues
    assert any("whitelist" in note.lower() for note in result.notes)


def test_disabled_suitability_check_does_not_fail():
    result = build_result(
        _matching_result("S9 - Made up status"),
        {
            "document_reference": "required",
            "revision": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            enabled=False, values=ISO_LIST
        ),
    )
    assert result.status == CheckStatus.MATCH
    assert CheckStatus.SUITABILITY_ERROR not in result.issues


def test_fail_on_error_false_warns_only():
    result = build_result(
        _matching_result("S9 - Made up status"),
        {
            "document_reference": "required",
            "revision": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            fail_on_error=False, values=ISO_LIST
        ),
    )
    assert result.status == CheckStatus.MATCH
    assert any("whitelist" in note.lower() for note in result.notes)


def test_bundled_config_loads_iso_list(config_dir: Path):
    config = load_config(config_dir)
    assert config.suitability_check is not None
    assert config.suitability_check.enabled
    assert "S3 - Review and comment" in config.suitability_check.values
    assert "S5 - Construction" in config.suitability_check.values
    assert "S4 - For Construction" in config.suitability_check.values
    assert "S5 - For Construction" in config.suitability_check.values
    assert "S4 - Suitable for building control approval" in config.suitability_check.values
    assert "S4 - For building control approval" in config.suitability_check.values
    assert config.suitability_check.purpose_enabled
    assert config.suitability_check.purpose_review == ["S3"]
    assert "S5 - Construction" in config.suitability_check.purpose_construction
    assert "S4 - For Construction" in config.suitability_check.purpose_construction
    assert "R459" in config.suitability_check.projects
    assert "S5 - For Construction" in config.suitability_check.projects["R459"]
    assert "A - Contractual" in config.suitability_check.projects["R459"]
    assert config.suitability_check.project_names["R459"] == "Oval C+D"
    assert "R456" in config.suitability_check.projects
    assert config.suitability_check.project_names["R456"] == "Trillium"
    assert config.suitability_check.projects["R456"] == config.suitability_check.projects["R459"]
    assert "J106309" in config.suitability_check.projects
    assert config.suitability_check.project_names["J106309"] == "Barking Riverside"
    assert "CR - Construction Record" in config.suitability_check.projects["J106309"]
    assert "S4 - Suitable for Other Stage Approvals" in config.suitability_check.projects["J106309"]
    assert "WCR" in config.suitability_check.projects
    assert config.suitability_check.project_names["WCR"] == "West Cromwell Road"
    assert config.client_check is not None
    assert config.client_check.projects["WCR"] == ["Seven Capital Woodrow"]
    assert config.client_check.projects["R459"] == ["Berkeley", "Berkeley Homes"]
    assert config.client_check.projects["R456"] == ["Berkeley", "Berkeley Homes"]
    assert config.client_check.projects["J106309"] == ["MEP", "MBS", "L&Q"]
    assert config.client_check.project_names["HPA"] == "Holloway Park"
    assert config.client_check.projects["HPA"] == ["London Square"]
    assert config.suitability_check.projects["WCR"] == [
        "A - Construction",
        "A - For Construction",
        "S4 - Construction",
        "S4 - For Construction",
        "S5 - Construction",
        "S5 - For Construction",
    ]
    assert "S5 - For Construction" in config.suitability_check.suggested
    assert config.suitability_check.suggested == config.suitability_check.projects["R459"]
    assert "HPA" in config.suitability_check.projects
    assert config.suitability_check.project_names["HPA"] == "Holloway Park"
    assert config.suitability_check.projects["HPA"] == config.suitability_check.projects["R459"]


def test_barking_riverside_uses_project_dropdown(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "J106309-MEP-02-ZZ-DR-X-600026-C01.pdf",
        document_reference="J106309-MEP-02-ZZ-DR-X-600026",
        title="Ground Floor GA",
        revision="C01",
        suitability="S4 - Suitable for Other Stage Approvals",
        client="MEP",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.SUITABILITY_ERROR not in result.issues
    assert result.purpose_list_official is True
    assert result.purpose_list_name == "Barking Riverside"
    assert "CR - Construction Record" in result.designer_purpose_values
    assert "S5 - For Construction" not in result.designer_purpose_values


def test_hpa_uses_standard_purpose_whitelist(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "HPA-MBS-D3-LG-DR-X-55103-P01.pdf",
        document_reference="HPA-MBS-D3-LG-DR-X-55103",
        title="Lighting layout",
        revision="P01",
        suitability="S3 - For Review & Comment",
        client="London Square",
    )
    config = load_config(config_dir)
    result = check_pdf(pdf, config)
    assert CheckStatus.SUITABILITY_ERROR not in result.issues
    assert result.purpose_list_official is True
    assert result.purpose_list_name == "Holloway Park"
    assert result.designer_purpose_values == config.suitability_check.projects["R459"]


def test_wcr_uses_construction_purpose_whitelist(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "WCR-MBS-B7-XX-DR-M-5301-C01.pdf",
        document_reference="WCR-MBS-B7-XX-DR-M-5301",
        title="Mechanical Services Layout",
        revision="C01",
        suitability="A - Construction",
        client="Seven Capital Woodrow",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.SUITABILITY_ERROR not in result.issues
    assert CheckStatus.PURPOSE_MISMATCH not in result.issues
    assert result.purpose_list_official is True
    assert result.purpose_list_name == "West Cromwell Road"
    assert result.designer_purpose_values == [
        "A - Construction",
        "A - For Construction",
        "S4 - Construction",
        "S4 - For Construction",
        "S5 - Construction",
        "S5 - For Construction",
    ]


def test_wcr_rejects_review_purpose(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "WCR-MBS-B7-XX-DR-M-5301-P01.pdf",
        document_reference="WCR-MBS-B7-XX-DR-M-5301",
        title="Mechanical Services Layout",
        revision="P01",
        suitability="S3 - For Review & Comment",
        client="Seven Capital Woodrow",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.SUITABILITY_ERROR in result.issues
    assert "S3 - For Review & Comment" not in result.designer_purpose_values


def test_pdf_accepted_iso_status(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
        suitability="S3 - Review and comment",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.status == CheckStatus.MATCH
    assert CheckStatus.SUITABILITY_ERROR not in result.issues


def test_pdf_flags_typo_status(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="P01",
        suitability="S3 - Reveu and comment",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.status == CheckStatus.SUITABILITY_ERROR
    assert any("Reveu" in note or "reveu" in note.lower() for note in result.notes)


def test_pdf_accepted_s5_construction(tmp_path: Path, config_dir: Path):
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-C01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Ground Floor GA",
        revision="C01",
        suitability="S5 - Construction",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert CheckStatus.SUITABILITY_ERROR not in result.issues
    assert CheckStatus.PURPOSE_MISMATCH not in result.issues


def test_purpose_families():
    assert suitability_purpose_family("S3 - Review & Comment") == "review"
    assert suitability_purpose_family("S3") == "review"
    assert suitability_purpose_family("S5 - Construction") == "construction"
    assert suitability_purpose_family("A - FOR CONSTRUCTION") == "construction"
    assert suitability_purpose_family("S2 - Suitable for tender") is None
    assert suitability_purpose_family("S4 - Suitable for building control approval") is None
    assert suitability_purpose_family("S4 - Stage approval") is None
    assert suitability_purpose_family("S5") is None


def test_purpose_family_uses_configured_lists():
    assert (
        suitability_purpose_family(
            "S4 - For building control approval",
            construction=["S4 - For building control approval"],
        )
        == "construction"
    )
    assert suitability_purpose_family("S3", review=["S2"]) is None


def test_p_revision_with_construction_purpose_is_flagged():
    assert revision_purpose_mismatch_note("P03", "S5 - CONSTRUCTION")
    assert revision_purpose_mismatch_note("C02", "S3 - Review and comment")
    assert revision_purpose_mismatch_note("P01", "S3 - Review and comment") is None
    assert revision_purpose_mismatch_note("C01", "S5 - Construction") is None
    assert revision_purpose_mismatch_note("P02", "S2 - Suitable for tender") is None


def test_build_result_flags_p_revision_with_construction_status():
    result = build_result(
        _matching_result("S5 - Construction"),
        {
            "document_reference": "required",
            "revision": "if_both_present",
            "title": "if_both_present",
            "suitability": "if_both_present",
            "date": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            values=["S3 - Review and comment", "S5 - Construction"]
        ),
    )
    assert CheckStatus.PURPOSE_MISMATCH in result.issues
    assert any("preliminary" in note.lower() for note in result.notes)


def test_build_result_flags_c_revision_with_review_status():
    result = DocumentResult(
        path=Path("ABC-WXY-ZZ-00-DR-A-0001-C01.pdf"),
        filename=FilenameFields(
            raw_stem="ABC-WXY-ZZ-00-DR-A-0001-C01",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="C01",
            parse_ok=True,
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="C01",
            title="Ground Floor GA",
            suitability="S3 - Review and comment",
        ),
    )
    result = build_result(
        result,
        {
            "document_reference": "required",
            "revision": "if_both_present",
            "title": "if_both_present",
            "suitability": "if_both_present",
            "date": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            values=["S3 - Review and comment", "S5 - Construction"]
        ),
    )
    assert CheckStatus.PURPOSE_MISMATCH in result.issues
    assert any("construction (C)" in note for note in result.notes)


def test_purpose_check_can_be_disabled():
    result = build_result(
        _matching_result("S5 - Construction"),
        {
            "document_reference": "required",
            "revision": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            values=["S5 - Construction"],
            purpose_enabled=False,
        ),
    )
    assert CheckStatus.PURPOSE_MISMATCH not in result.issues


def test_for_construction_matches_construction_wording():
    from drawing_qa.suitability import suitability_is_allowed

    oval = [
        "S3 - For Review & Comment",
        "S5 - For Construction",
    ]
    assert suitability_is_allowed("S5 - FOR CONSTRUCTION", oval)
    assert suitability_is_allowed("S3 - REVIEW & COMMENT", oval)
    assert suitability_is_allowed("S3 - REVIEW & COMMENTS", oval)
    assert not suitability_is_allowed("S4 - CONSTRUCTION", oval)
    barking = [
        "CR - Construction Record",
        "S4 - Suitable for Building Control Approval",
        "S4 - Suitable for Other Stage Approvals",
    ]
    assert suitability_is_allowed("S4 - Suitable for Other Stage Approval", barking)
    assert suitability_is_allowed("S4 - Suitable for Other Stage Approvals", barking)


def test_duplicate_trailing_suitability_code_is_stripped():
    from drawing_qa.tokens import extract_suitability

    assert extract_suitability("FOR CONSTRUCTION S5 S5") == "S5 - FOR CONSTRUCTION"
    assert extract_suitability("P1 - Preliminary Issue") == "P1 - Preliminary Issue"


def test_project_whitelist_used_for_matching_project_code():
    result = DocumentResult(
        path=Path("R459-MBS-DZ-ZZ-DR-W-60002-C01.pdf"),
        filename=FilenameFields(
            raw_stem="R459-MBS-DZ-ZZ-DR-W-60002-C01",
            document_reference="R459-MBS-DZ-ZZ-DR-W-60002",
            revision="C01",
            parse_ok=True,
            parts={"project": "R459"},
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="R459-MBS-DZ-ZZ-DR-W-60002",
            revision="C01",
            title="Ground Floor GA",
            suitability="S5 - FOR CONSTRUCTION",
        ),
    )
    result = build_result(
        result,
        {
            "document_reference": "required",
            "revision": "if_both_present",
            "title": "if_both_present",
            "suitability": "if_both_present",
            "date": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            values=["S3 - Review and comment"],
            projects={"R459": ["S5 - For Construction"]},
            purpose_enabled=False,
        ),
    )
    assert CheckStatus.SUITABILITY_ERROR not in result.issues


def test_project_whitelist_rejects_s4_construction_when_not_listed():
    result = DocumentResult(
        path=Path("R459-MBS-DZ-ZZ-DR-W-60008-C01.pdf"),
        filename=FilenameFields(
            raw_stem="R459-MBS-DZ-ZZ-DR-W-60008-C01",
            document_reference="R459-MBS-DZ-ZZ-DR-W-60008",
            revision="C01",
            parse_ok=True,
            parts={"project": "R459"},
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="R459-MBS-DZ-ZZ-DR-W-60008",
            revision="C01",
            title="Ground Floor GA",
            suitability="S4 - CONSTRUCTION",
        ),
    )
    result = build_result(
        result,
        {
            "document_reference": "required",
            "revision": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            values=["S4 - Construction", "S5 - For Construction"],
            projects={"R459": ["S5 - For Construction", "S4 - For Stage Approval"]},
            purpose_enabled=False,
        ),
    )
    assert CheckStatus.SUITABILITY_ERROR in result.issues


def test_allowed_values_fall_back_to_suggested():
    iso = ["S4 - Construction", "S5 - For Construction"]
    suggested = ["S5 - For Construction", "S4 - For Stage Approval"]
    assert allowed_values_for_project("ABC", iso, {}, suggested=suggested) == suggested
    assert allowed_values_for_project(
        "R459",
        iso,
        {"R459": ["S3 - For Review & Comment"]},
        suggested=suggested,
    ) == ["S3 - For Review & Comment"]
    assert allowed_values_for_project("ABC", iso, None) == iso


def test_unknown_project_uses_suggested_not_iso_values():
    result = DocumentResult(
        path=Path("ABC-WXY-ZZ-00-DR-A-0001-C01.pdf"),
        filename=FilenameFields(
            raw_stem="ABC-WXY-ZZ-00-DR-A-0001-C01",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="C01",
            parse_ok=True,
            parts={"project": "ABC"},
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="C01",
            title="Ground Floor GA",
            suitability="S4 - Construction",
        ),
    )
    result = build_result(
        result,
        {
            "document_reference": "required",
            "revision": "if_both_present",
        },
        suitability_check_config=SuitabilityCheckConfig(
            values=["S4 - Construction", "S5 - For Construction"],
            suggested=["S5 - For Construction", "S4 - For Stage Approval"],
            purpose_enabled=False,
        ),
    )
    assert CheckStatus.SUITABILITY_ERROR in result.issues
    assert CheckStatus.PURPOSE_INCONSISTENT not in result.issues
    assert result.designer_purpose_values == [
        "S5 - For Construction",
        "S4 - For Stage Approval",
    ]
    assert result.purpose_list_official is False
