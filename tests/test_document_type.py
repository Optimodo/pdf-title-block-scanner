from pathlib import Path

from drawing_qa.checker import check_pdf
from drawing_qa.checks import CheckOptions
from drawing_qa.compare import build_result
from drawing_qa.config_loader import DocumentTypeCheckConfig, load_config
from drawing_qa.document_type import iso_type_from_doc_ref, title_looks_like_schematic
from drawing_qa.designer_brief import designer_actions
from drawing_qa.models import (
    CheckStatus,
    DocumentResult,
    FilenameFields,
    TitleBlockFields,
    finalize_status,
)
from tests.pdf_fixtures import write_mbs_right_pdf

COMPARE_RULES = {
    "document_reference": "required",
    "revision": "if_both_present",
    "title": "if_both_present",
    "suitability": "if_both_present",
    "date": "if_both_present",
}


def test_iso_type_is_fifth_segment():
    assert iso_type_from_doc_ref("J106309-MBS-ZZ-ZZ-DR-X-620301") == "DR"
    assert iso_type_from_doc_ref("R456-MBS-BI-ZZ-SH-W-605-001") == "SH"
    assert iso_type_from_doc_ref("HPA-MBS-C1-ZZ-SM-X-52007") == "SM"


def test_schematic_word_is_whole_word_only():
    assert title_looks_like_schematic("Block D Combined Services Schematic")
    assert title_looks_like_schematic("LTHW schematics — sheet 1")
    assert not title_looks_like_schematic("Apartment Combined Services Layout")
    assert not title_looks_like_schematic("schematicism")


def test_bundled_config_loads_schematic_types():
    from drawing_qa.paths import bundled_config_dir

    types = load_config(bundled_config_dir()).document_type_check.schematic_types
    assert types["R459"] == "DR"
    assert types["R456"] == "SH"
    assert types["HPA"] == "SM"
    assert types["WCR"] == "SC"
    assert types["J106309"] == "SC"


def _drawing(
    *,
    project: str,
    type_code: str,
    title: str,
    number: str = "0001",
) -> DocumentResult:
    ref = f"{project}-MBS-ZZ-ZZ-{type_code}-W-{number}"
    return DocumentResult(
        path=Path(f"{ref}-P01.pdf"),
        filename=FilenameFields(
            raw_stem=f"{ref}-P01",
            document_reference=ref,
            title=title,
            revision="P01",
            parse_ok=True,
            parts={"project": project, "type": type_code, "number": number},
        ),
        titleblock=TitleBlockFields(
            layout_id="mbs_right",
            document_reference=ref,
            title=title,
            revision="P01",
        ),
        status=CheckStatus.MATCH,
    )


def _type_config() -> DocumentTypeCheckConfig:
    return DocumentTypeCheckConfig(
        schematic_types={
            "R459": "DR",
            "R456": "SH",
            "HPA": "SM",
            "WCR": "SC",
            "J106309": "SC",
        }
    )


def test_trillium_schematic_with_dr_is_flagged():
    result = build_result(
        _drawing(project="R456", type_code="DR", title="Combined Services Schematic"),
        COMPARE_RULES,
        document_type_config=_type_config(),
    )
    finalize_status(result)
    assert CheckStatus.SCHEMATIC_TYPE in result.issues
    assert "SH" in " ".join(result.notes)
    assert "DR" in " ".join(result.notes)
    text = designer_actions(result)
    assert "schematic" in text.lower()
    assert "SH" in text


def test_trillium_schematic_with_sh_is_ok():
    result = build_result(
        _drawing(project="R456", type_code="SH", title="Combined Services Schematic"),
        COMPARE_RULES,
        document_type_config=_type_config(),
    )
    finalize_status(result)
    assert CheckStatus.SCHEMATIC_TYPE not in result.issues
    assert result.status == CheckStatus.MATCH


def test_oval_schematic_keeps_dr():
    result = build_result(
        _drawing(project="R459", type_code="DR", title="Plant Schematic"),
        COMPARE_RULES,
        document_type_config=_type_config(),
    )
    finalize_status(result)
    assert CheckStatus.SCHEMATIC_TYPE not in result.issues


def test_layout_title_is_not_checked():
    result = build_result(
        _drawing(project="R456", type_code="DR", title="Apartment Combined Services Layout"),
        COMPARE_RULES,
        document_type_config=_type_config(),
    )
    finalize_status(result)
    assert CheckStatus.SCHEMATIC_TYPE not in result.issues


def test_holloway_barking_and_wcr_codes():
    cases = [
        ("HPA", "DR", "SM", True),
        ("HPA", "SM", "SM", False),
        ("WCR", "DR", "SC", True),
        ("J106309", "DR", "SC", True),
        ("J106309", "SC", "SC", False),
    ]
    for project, got, expected, flagged in cases:
        result = build_result(
            _drawing(project=project, type_code=got, title="Services Schematic"),
            COMPARE_RULES,
            document_type_config=_type_config(),
        )
        finalize_status(result)
        if flagged:
            assert CheckStatus.SCHEMATIC_TYPE in result.issues, project
            assert result.schematic_type_expected == expected
        else:
            assert CheckStatus.SCHEMATIC_TYPE not in result.issues, project


def test_unlisted_project_is_skipped():
    result = build_result(
        _drawing(project="ZZZ", type_code="DR", title="Something Schematic"),
        COMPARE_RULES,
        document_type_config=_type_config(),
    )
    finalize_status(result)
    assert CheckStatus.SCHEMATIC_TYPE not in result.issues


def test_schematic_type_can_be_disabled():
    result = build_result(
        _drawing(project="R456", type_code="DR", title="Combined Services Schematic"),
        COMPARE_RULES,
        document_type_config=_type_config(),
        check_options=CheckOptions(enabled=frozenset({"mismatch"})),
    )
    finalize_status(result)
    assert CheckStatus.SCHEMATIC_TYPE not in result.issues


def test_real_pdf_trillium_schematic_with_dr(tmp_path: Path, config_dir: Path):
    pdf = write_mbs_right_pdf(
        tmp_path / "R456-MBS-BI-ZZ-DR-W-605001-P01.pdf",
        document_reference="R456-MBS-BI-ZZ-DR-W-605001",
        title="Block I Combined Services Schematic",
        revision="P01",
        suitability="S3",
        client="Berkeley Homes",
    )
    result = check_pdf(pdf, load_config(config_dir))
    assert result.filename.parts.get("type") == "DR"
    assert CheckStatus.SCHEMATIC_TYPE in result.issues
