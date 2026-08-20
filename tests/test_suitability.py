from pathlib import Path

from drawing_qa.checker import check_pdf
from drawing_qa.compare import build_result
from drawing_qa.config_loader import SuitabilityCheckConfig, load_config
from drawing_qa.models import CheckStatus, DocumentResult, FilenameFields, TitleBlockFields
from drawing_qa.suitability import normalize_suitability, suitability_is_allowed
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
