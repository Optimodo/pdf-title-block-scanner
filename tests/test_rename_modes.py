"""Tests for mismatch-only filename suggestions (preserve existing stem suffix)."""

from pathlib import Path

from drawing_qa.models import (
    CheckStatus,
    DocumentResult,
    FieldComparison,
    FilenameFields,
    TitleBlockFields,
)
from drawing_qa.validation import standardize_filename, suggest_filename


def _mismatch(
    path: Path,
    *,
    filename_ref: str,
    titleblock_ref: str,
    title: str | None = "Floor Plan",
    revision: str | None = "P01",
) -> DocumentResult:
    return DocumentResult(
        path=path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference=titleblock_ref,
            title=title,
            revision=revision,
        ),
        filename=FilenameFields(
            raw_stem=path.stem,
            document_reference=filename_ref,
            parse_ok=True,
        ),
        comparisons=[
            FieldComparison(
                "document_reference",
                filename_ref,
                titleblock_ref,
                False,
                "mismatch",
            )
        ],
    )


def test_suggest_filename_replaces_doc_ref_keeps_revision_suffix():
    result = _mismatch(
        Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001-P01.pdf"),
        filename_ref="ABC-XYZ-ZZ-00-DR-M-0001",
        titleblock_ref="ABC-XYZ-ZZ-00-DR-M-1234",
    )
    assert suggest_filename(result) == "ABC-XYZ-ZZ-00-DR-M-1234-P01.pdf"


def test_suggest_filename_keeps_existing_title_and_revision():
    result = _mismatch(
        Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001_Ground Floor_C02.pdf"),
        filename_ref="ABC-XYZ-ZZ-00-DR-M-0001",
        titleblock_ref="ABC-XYZ-ZZ-00-DR-M-1234",
    )
    assert suggest_filename(result) == "ABC-XYZ-ZZ-00-DR-M-1234_Ground Floor_C02.pdf"


def test_suggest_filename_handles_underscore_doc_ref():
    result = _mismatch(
        Path("/tmp/ABC_XYZ_ZZ_00_DR_M_0001_Floor Plan_P01.pdf"),
        filename_ref="ABC-XYZ-ZZ-00-DR-M-0001",
        titleblock_ref="ABC-XYZ-ZZ-00-DR-M-1234",
    )
    assert suggest_filename(result) == "ABC-XYZ-ZZ-00-DR-M-1234_Floor Plan_P01.pdf"


def test_suggest_filename_not_offered_when_doc_ref_already_matches():
    """Title/revision mismatches must not trigger a rename suggestion."""
    result = DocumentResult(
        path=Path("/tmp/ABC-XYZ-ZZ-00-DR-M-1234_Wrong Title_P01.pdf"),
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-1234_Wrong Title_P01",
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Wrong Title",
            revision="P01",
            parse_ok=True,
        ),
        comparisons=[
            FieldComparison(
                "document_reference",
                "ABC-XYZ-ZZ-00-DR-M-1234",
                "ABC-XYZ-ZZ-00-DR-M-1234",
                True,
                "equal",
            ),
            FieldComparison(
                "title",
                "Wrong Title",
                "Floor Plan",
                False,
                "mismatch",
            ),
        ],
    )
    assert suggest_filename(result) is None


def test_suggest_filename_not_offered_for_match():
    result = DocumentResult(
        path=Path("/tmp/ABC-XYZ-ZZ-00-DR-M-1234.pdf"),
        status=CheckStatus.MATCH,
        titleblock=TitleBlockFields(document_reference="ABC-XYZ-ZZ-00-DR-M-1234"),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-1234",
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            parse_ok=True,
        ),
        comparisons=[
            FieldComparison(
                "document_reference",
                "ABC-XYZ-ZZ-00-DR-M-1234",
                "ABC-XYZ-ZZ-00-DR-M-1234",
                True,
                "equal",
            )
        ],
    )
    assert suggest_filename(result) is None


def test_suggest_filename_does_not_strip_to_doc_ref_only():
    result = _mismatch(
        Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001 - Site Plan.pdf"),
        filename_ref="ABC-XYZ-ZZ-00-DR-M-0001",
        titleblock_ref="ABC-XYZ-ZZ-00-DR-M-1234",
    )
    suggested = suggest_filename(result)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234 - Site Plan.pdf"
    assert suggested != "ABC-XYZ-ZZ-00-DR-M-1234.pdf"


def test_standardize_filename_includes_title_and_revision():
    result = DocumentResult(
        path=Path("/tmp/ABC-XYZ-ZZ-00-DR-M-1234.pdf"),
        status=CheckStatus.MATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-1234",
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            parse_ok=True,
        ),
    )

    assert standardize_filename(result) == "ABC-XYZ-ZZ-00-DR-M-1234_Floor Plan_P01.pdf"


def test_standardize_filename_sanitizes_illegal_title_chars():
    result = DocumentResult(
        path=Path("/tmp/ABC-XYZ-ZZ-00-DR-M-1234.pdf"),
        status=CheckStatus.MATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title='Level 1 / "GA"',
            revision="C02",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-1234",
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            parse_ok=True,
        ),
    )

    assert standardize_filename(result) == "ABC-XYZ-ZZ-00-DR-M-1234_Level 1 - GA_C02.pdf"


def test_standardize_filename_omits_missing_title():
    result = DocumentResult(
        path=Path("/tmp/ABC-XYZ-ZZ-00-DR-M-1234.pdf"),
        status=CheckStatus.INCOMPLETE,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title=None,
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-1234",
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            parse_ok=True,
        ),
    )

    assert standardize_filename(result) == "ABC-XYZ-ZZ-00-DR-M-1234_P01.pdf"
