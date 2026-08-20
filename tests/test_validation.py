from pathlib import Path

from drawing_qa.checker import check_pdf, check_paths
from drawing_qa.config_loader import load_config
from drawing_qa.models import CheckStatus
from tests.pdf_fixtures import write_bottom_right_pdf


def test_detects_duplicate_document_references(tmp_path: Path, config_dir: Path):
    """Test that duplicate document references are detected."""
    # Create two PDFs with same document reference
    pdf1 = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Floor Plan",
        revision="P01",
    )
    pdf2 = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-C02.pdf",  # Different filename
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",  # Same doc ref
        title="Floor Plan",
        revision="C02",
    )
    
    config = load_config(config_dir)
    results = check_paths([pdf1, pdf2], config)
    
    # Both should be flagged as duplicates
    assert len(results) == 2
    assert all(r.status == CheckStatus.DUPLICATE_REFERENCE for r in results)
    assert all("Duplicate document reference" in " ".join(r.notes) for r in results)


def test_date_regression_in_history(tmp_path: Path, config_dir: Path):
    """Test that date mismatches between current and history are detected."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P03.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Floor Plan",
        revision="P03",
        date="10.01.24",
        history=[
            ("P01", "15.01.24", "First issue"),
            ("P02", "10.03.24", "Update"),
            ("P03", "05.05.24", "Final"),  # History date doesn't match current
        ],
    )
    
    config = load_config(config_dir)
    result = check_pdf(pdf, config)
    
    # History mismatch should be detected (current date doesn't match latest history)
    assert result.status == CheckStatus.HISTORY_MISMATCH
    # Just verify some notes exist about the mismatch
    assert len(result.notes) > 0


def test_filename_suggestion_for_mismatch(tmp_path: Path, config_dir: Path):
    """Test that filename suggestions are generated for mismatches."""
    # Use a valid ISO 19650 filename that doesn't match the title block
    pdf = write_bottom_right_pdf(
        tmp_path / "XYZ-DEF-AA-BB-DR-M-9999-P01.pdf",  # Valid 7-field format but wrong doc ref
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",  # Correct doc ref in title block
        title="Floor Plan",
        revision="P01",
    )
    
    config = load_config(config_dir)
    results = check_paths([pdf], config)
    result = results[0]
    
    assert result.status == CheckStatus.MISMATCH
    assert result.suggested_filename is not None
    assert "ABC-WXY-ZZ-00-DR-A-0001" in result.suggested_filename


def test_dwg_pairing_exact_match(tmp_path: Path, config_dir: Path):
    """Test that DWG files with exact matching names are paired."""
    # Create PDF
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Floor Plan",
        revision="P01",
    )
    
    # Create matching DWG (just an empty file for testing)
    dwg = tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.dwg"
    dwg.write_text("")
    
    config = load_config(config_dir)
    results = check_paths([pdf], config)
    result = results[0]
    
    assert result.paired_dwg == dwg
    assert result.dwg_mismatch is False


def test_dwg_pairing_with_naming_mismatch(tmp_path: Path, config_dir: Path):
    """Test that DWG files with different separators are detected as mismatches."""
    # Create PDF with dashes
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Floor Plan",
        revision="P01",
    )
    
    # Create DWG with underscores instead of dashes
    dwg = tmp_path / "ABC_WXY_ZZ_00_DR_A_0001_P01.dwg"
    dwg.write_text("")
    
    config = load_config(config_dir)
    results = check_paths([pdf], config)
    result = results[0]
    
    assert result.paired_dwg == dwg
    assert result.dwg_mismatch is True
    assert any("DWG file naming mismatch" in note for note in result.notes)


def test_no_dwg_pairing_when_dwg_absent(tmp_path: Path, config_dir: Path):
    """Test that absence of DWG file is handled gracefully."""
    pdf = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Floor Plan",
        revision="P01",
    )
    
    config = load_config(config_dir)
    results = check_paths([pdf], config)
    result = results[0]
    
    assert result.paired_dwg is None
    assert result.dwg_mismatch is False


def test_duplicates_dont_override_serious_issues(tmp_path: Path, config_dir: Path):
    """Test that duplicate detection doesn't override more serious statuses."""
    # Create two PDFs with same doc ref but one has a mismatch
    pdf1 = write_bottom_right_pdf(
        tmp_path / "ABC-WXY-ZZ-00-DR-A-0001-P01.pdf",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        title="Floor Plan",
        revision="P01",
    )
    pdf2 = write_bottom_right_pdf(
        tmp_path / "XYZ-DEF-AA-BB-DR-M-9999-C02.pdf",  # Valid 7-field format but wrong doc ref
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",  # Same doc ref (duplicate)
        title="Floor Plan",
        revision="C02",
    )
    
    config = load_config(config_dir)
    results = check_paths([pdf1, pdf2], config)
    
    # pdf1 should be DUPLICATE_REFERENCE
    # pdf2 should be MISMATCH (more serious than duplicate)
    assert results[0].status == CheckStatus.DUPLICATE_REFERENCE
    assert results[1].status == CheckStatus.MISMATCH
    
    # Both should have duplicate notes though
    assert all("Duplicate document reference" in " ".join(r.notes) for r in results)
