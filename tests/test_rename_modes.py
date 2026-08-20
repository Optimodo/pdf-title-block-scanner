"""Tests for different rename modes (doc ref only vs. full details)."""

from pathlib import Path

from drawing_qa.models import CheckStatus, DocumentResult, FilenameFields, TitleBlockFields
from drawing_qa.validation import suggest_filename


def test_suggest_filename_doc_ref_only():
    """Default mode: only document reference in filename."""
    pdf_path = Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001.pdf")
    
    result = DocumentResult(
        path=pdf_path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-0001",
            document_reference="ABC-XYZ-ZZ-00-DR-M-0001",
            parse_ok=True,
        ),
    )
    
    # Default: only document reference
    suggested = suggest_filename(result, include_title=False, include_revision=False)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234.pdf"
    assert "_Floor Plan" not in suggested
    assert "P01" not in suggested


def test_suggest_filename_with_title():
    """Include title in suggested filename."""
    pdf_path = Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001.pdf")
    
    result = DocumentResult(
        path=pdf_path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-0001",
            document_reference="ABC-XYZ-ZZ-00-DR-M-0001",
            parse_ok=True,
        ),
    )
    
    suggested = suggest_filename(result, include_title=True, include_revision=False)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234_Floor Plan.pdf"


def test_suggest_filename_with_revision():
    """Include revision in suggested filename."""
    pdf_path = Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001.pdf")
    
    result = DocumentResult(
        path=pdf_path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-0001",
            document_reference="ABC-XYZ-ZZ-00-DR-M-0001",
            parse_ok=True,
        ),
    )
    
    suggested = suggest_filename(result, include_title=False, include_revision=True)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234-P01.pdf"


def test_suggest_filename_full_details():
    """Full mode: document reference, title, and revision."""
    pdf_path = Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001.pdf")
    
    result = DocumentResult(
        path=pdf_path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-0001",
            document_reference="ABC-XYZ-ZZ-00-DR-M-0001",
            parse_ok=True,
        ),
    )
    
    suggested = suggest_filename(result, include_title=True, include_revision=True)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234_Floor Plan_P01.pdf"


def test_suggest_filename_no_title_available():
    """Handle case where title is missing."""
    pdf_path = Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001.pdf")
    
    result = DocumentResult(
        path=pdf_path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title=None,
            revision="P01",
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-0001",
            document_reference="ABC-XYZ-ZZ-00-DR-M-0001",
            parse_ok=True,
        ),
    )
    
    # Even with include_title=True, should not fail if title is None
    suggested = suggest_filename(result, include_title=True, include_revision=True)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234-P01.pdf"


def test_suggest_filename_no_revision_available():
    """Handle case where revision is missing."""
    pdf_path = Path("/tmp/ABC-XYZ-ZZ-00-DR-M-0001.pdf")
    
    result = DocumentResult(
        path=pdf_path,
        status=CheckStatus.MISMATCH,
        titleblock=TitleBlockFields(
            document_reference="ABC-XYZ-ZZ-00-DR-M-1234",
            title="Floor Plan",
            revision=None,
        ),
        filename=FilenameFields(
            raw_stem="ABC-XYZ-ZZ-00-DR-M-0001",
            document_reference="ABC-XYZ-ZZ-00-DR-M-0001",
            parse_ok=True,
        ),
    )
    
    # Even with include_revision=True, should not fail if revision is None
    suggested = suggest_filename(result, include_title=True, include_revision=True)
    assert suggested == "ABC-XYZ-ZZ-00-DR-M-1234_Floor Plan.pdf"
