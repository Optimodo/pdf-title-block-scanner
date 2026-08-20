from pathlib import Path

from drawing_qa.checker import check_pdf
from drawing_qa.config_loader import load_config
from drawing_qa.models import CheckStatus
from tests.pdf_fixtures import write_bottom_right_pdf


def test_detects_spelling_errors_in_title(tmp_path: Path, config_dir: Path):
    """Test that spelling errors are detected in drawing titles."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Gorund Floor Plan",  # "Gorund" is misspelled
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    
    assert result.status == CheckStatus.SPELLING_ERROR
    assert len(result.spelling_errors) > 0
    assert "gorund" in [e.lower() for e in result.spelling_errors]
    assert any("spelling" in note.lower() for note in result.notes)


def test_mep_terms_not_flagged_as_errors(tmp_path: Path, config_dir: Path):
    """Test that MEP and construction terms are not flagged as spelling errors."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="HVAC Layout Plantroom Level LG",  # All valid MEP/construction terms
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    
    # Should not have spelling errors
    assert result.status == CheckStatus.MATCH
    assert len(result.spelling_errors) == 0


def test_technical_abbreviations_not_flagged(tmp_path: Path, config_dir: Path):
    """Test that common technical abbreviations are whitelisted."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="SVP RWP DHW Layout Mezzanine",  # All common abbreviations
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    
    assert result.status == CheckStatus.MATCH
    assert len(result.spelling_errors) == 0


def test_spelling_error_includes_suggestions(tmp_path: Path, config_dir: Path):
    """Test that spelling errors include suggestions."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Electrcal Layout",  # "Electrcal" missing 'i'
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    
    assert result.status == CheckStatus.SPELLING_ERROR
    assert "electrcal" in [e.lower() for e in result.spelling_errors]
    # Check that suggestions are provided in notes
    spelling_note = [n for n in result.notes if "spelling" in n.lower()][0]
    assert "electrcal" in spelling_note.lower()


def test_spelling_preserves_mismatch_status(tmp_path: Path, config_dir: Path):
    """Test that spelling errors don't override more serious issues like MISMATCH."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Gorund Floor Plan",  # Misspelled
        revision="C02",  # Doesn't match filename
    )
    result = check_pdf(pdf, load_config(config_dir))
    
    # Should be MISMATCH (more serious) not SPELLING_ERROR
    assert result.status == CheckStatus.MISMATCH
    # But spelling errors should still be noted
    assert len(result.spelling_errors) > 0


def test_uk_spelling_accepted(tmp_path: Path, config_dir: Path):
    """Test that UK English spelling is accepted."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Vapour Barrier Detail Colour Coded",  # UK spellings
        revision="P01",
    )
    result = check_pdf(pdf, load_config(config_dir))
    
    # UK spellings should be accepted
    assert result.status == CheckStatus.MATCH
    assert len(result.spelling_errors) == 0
