from pathlib import Path

from drawing_qa.checker import check_pdf
from drawing_qa.compare import build_result
from drawing_qa.config_loader import LevelCheckConfig, load_config
from drawing_qa.designer_brief import designer_actions
from drawing_qa.level import iso_level_from_doc_ref, level_is_allowed
from drawing_qa.models import (
    CheckStatus,
    DocumentResult,
    FilenameFields,
    TitleBlockFields,
    finalize_status,
)
from drawing_qa.paths import bundled_config_dir
from tests.pdf_fixtures import write_mbs_right_pdf

COMPARE_RULES = {
    "document_reference": "required",
    "revision": "if_both_present",
    "title": "if_both_present",
    "suitability": "if_both_present",
    "date": "if_both_present",
}


def test_iso_level_is_fourth_segment():
    assert iso_level_from_doc_ref("R456-MBS-BI-B1-DR-W-605-001") == "B1"
    assert iso_level_from_doc_ref("R456-MBS-BI-00-DR-W-600-101") == "00"
    assert iso_level_from_doc_ref("R456-MBS-BI-ZZ-DR-W-605-001") == "ZZ"
    assert iso_level_from_doc_ref("R456-MBS-BI-BA-DR-W-605-001") == "BA"


def test_bundled_trillium_list_accepts_floors_and_rejects_ba():
    config = load_config(bundled_config_dir())
    allowed = config.level_check.projects["R456"]
    assert config.level_check.project_names["R456"] == "Trillium"
    assert "B1" in allowed
    assert "B2" in allowed
    assert "B3" in allowed
    assert "00" in allowed
    assert "40" in allowed
    assert "ZZ" in allowed
    assert "BA" not in allowed
    assert level_is_allowed("B1", allowed)
    assert not level_is_allowed("BA", allowed)


def _drawing(*, project: str, level: str, number: str = "0001") -> DocumentResult:
    ref = f"{project}-MBS-BI-{level}-DR-W-{number}"
    return DocumentResult(
        path=Path(f"{ref}-P01.pdf"),
        filename=FilenameFields(
            raw_stem=f"{ref}-P01",
            document_reference=ref,
            title="Combined Services",
            revision="P01",
            parse_ok=True,
            parts={"project": project, "level": level, "number": number},
        ),
        titleblock=TitleBlockFields(
            layout_id="mbs_right",
            document_reference=ref,
            title="Combined Services",
            revision="P01",
        ),
        status=CheckStatus.MATCH,
    )


def _level_config() -> LevelCheckConfig:
    return LevelCheckConfig(
        projects={"R456": ["B1", "B2", "B3", "00", "ZZ"]},
        project_names={"R456": "Trillium"},
        hints={"R456": {"BA": "Basement must be B1, B2, or B3, not BA."}},
    )


def test_trillium_ba_is_flagged():
    result = build_result(
        _drawing(project="R456", level="BA"),
        COMPARE_RULES,
        level_check_config=_level_config(),
    )
    finalize_status(result)
    assert CheckStatus.LEVEL_ERROR in result.issues
    notes = " ".join(result.notes)
    assert "BA" in notes
    assert "B1" in notes
    assert "4th" in notes
    assert "Basement" in designer_actions(result)


def test_trillium_b1_and_ground_are_accepted():
    for level in ("B1", "00", "ZZ"):
        result = build_result(
            _drawing(project="R456", level=level),
            COMPARE_RULES,
            level_check_config=_level_config(),
        )
        finalize_status(result)
        assert CheckStatus.LEVEL_ERROR not in result.issues, level


def test_oval_has_no_level_list_so_ba_is_not_flagged():
    result = build_result(
        _drawing(project="R459", level="BA"),
        COMPARE_RULES,
        level_check_config=_level_config(),
    )
    finalize_status(result)
    assert CheckStatus.LEVEL_ERROR not in result.issues


def test_pdf_trillium_ba_is_flagged(tmp_path: Path, config_dir: Path):
    path = write_mbs_right_pdf(
        tmp_path / "R456-MBS-BI-BA-DR-W-605001-P01.pdf",
        document_reference="R456-MBS-BI-BA-DR-W-605001",
        title="Basement combined services",
        revision="P01",
    )
    result = check_pdf(path, load_config(config_dir))
    assert CheckStatus.LEVEL_ERROR in result.issues


def test_pdf_trillium_b1_is_accepted(tmp_path: Path, config_dir: Path):
    path = write_mbs_right_pdf(
        tmp_path / "R456-MBS-BI-B1-DR-W-605001-P01.pdf",
        document_reference="R456-MBS-BI-B1-DR-W-605001",
        title="Basement combined services",
        revision="P01",
    )
    result = check_pdf(path, load_config(config_dir))
    assert CheckStatus.LEVEL_ERROR not in result.issues
