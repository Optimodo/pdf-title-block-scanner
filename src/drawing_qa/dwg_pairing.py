"""DWG file pairing detection and validation.

Detects when DWG files should be paired with PDFs based on naming conventions,
and flags mismatches in naming patterns (underscore vs dash, etc.).
"""

from __future__ import annotations

from pathlib import Path

from drawing_qa.docref import parse_name_without_ext
from drawing_qa.models import DocumentResult


def find_dwg_files(folder: Path) -> list[Path]:
    """Find all DWG files in a folder.
    
    Args:
        folder: Folder to search
        
    Returns:
        List of DWG file paths
    """
    dwgs = []
    for ext in (".dwg", ".DWG"):
        dwgs.extend(folder.glob(f"*{ext}"))
    return sorted(dwgs)


def normalize_for_pairing(filename: str) -> str:
    """Normalize filename for pairing comparison.
    
    Removes extension and normalizes common variations:
    - Underscores to dashes
    - Multiple spaces to single space
    - Case insensitive
    
    Args:
        filename: Filename to normalize
        
    Returns:
        Normalized name for comparison
    """
    # Remove extension
    name = Path(filename).stem
    
    # Parse using docref parser which normalizes ISO 19650 patterns
    parsed = parse_name_without_ext(name)
    if parsed and parsed.doc_ref:
        # Use the normalized document reference + any suffix
        parts = [parsed.doc_ref]
        if parsed.title:
            parts.append(parsed.title)
        if parsed.revision_pc:
            parts.append(parsed.revision_pc)
        normalized = "-".join(parts)
    else:
        # Fallback: simple normalization
        normalized = name.replace("_", "-").replace("  ", " ").strip()
    
    return normalized.lower()


def find_paired_dwg(pdf_path: Path, dwg_files: list[Path]) -> tuple[Path | None, bool]:
    """Find DWG file that should be paired with this PDF.
    
    Returns both the paired DWG (if found) and whether there's a naming mismatch.
    
    A mismatch means:
    - DWG found with similar name but different separators (underscore vs dash)
    - DWG found with extra/missing suffixes
    
    Args:
        pdf_path: Path to PDF file
        dwg_files: List of available DWG files in same folder
        
    Returns:
        Tuple of (paired_dwg_path, has_mismatch)
        - paired_dwg_path: Path to paired DWG or None
        - has_mismatch: True if naming doesn't match exactly
    """
    pdf_stem = pdf_path.stem
    pdf_normalized = normalize_for_pairing(pdf_stem)
    
    # First check for exact match (ignoring case and extension)
    for dwg in dwg_files:
        if dwg.stem.lower() == pdf_stem.lower():
            return dwg, False
    
    # Check for normalized match (handles underscore/dash differences)
    for dwg in dwg_files:
        dwg_normalized = normalize_for_pairing(dwg.stem)
        if dwg_normalized == pdf_normalized:
            # Found a match but names don't match exactly
            return dwg, True
    
    return None, False


def check_dwg_pairing(
    results: list[DocumentResult],
    folder: Path,
) -> list[DocumentResult]:
    """Check for DWG pairing issues across all results.
    
    Updates results with paired_dwg and dwg_mismatch flags.
    Adds notes when mismatches are found.
    
    Args:
        results: List of document results
        folder: Folder containing the PDFs (and potentially DWGs)
        
    Returns:
        Updated list of results with DWG pairing information
    """
    dwg_files = find_dwg_files(folder)
    for result in results:
        result.dwg_files_present = bool(dwg_files)
        if not dwg_files:
            continue
        paired_dwg, has_mismatch = find_paired_dwg(result.path, dwg_files)
        if paired_dwg:
            result.paired_dwg = paired_dwg
            result.dwg_mismatch = has_mismatch
            if has_mismatch:
                note = (
                    f"DWG file naming mismatch: PDF '{result.path.name}' "
                    f"paired with DWG '{paired_dwg.name}' (differs in separators/format)"
                )
                result.notes.append(note)
        else:
            result.notes.append("No matching DWG in this folder")
    return results


# Comment on DWG file reading capability:
"""
## Reading DWG Files in Python

Reading and parsing DWG files to extract title block information is **technically possible 
but highly complex** for the following reasons:

### Challenges:

1. **Proprietary Format**: DWG is a closed, proprietary format owned by Autodesk. While 
   the Open Design Alliance (ODA) provides libraries, they're not simple Python packages.

2. **Python Libraries**:
   - **ezdxf**: Can read DXF (text-based CAD format) but NOT DWG directly
   - **pyautocad**: Requires AutoCAD to be installed (uses COM automation on Windows)
   - **ODA File Converter**: Can convert DWG→DXF, but requires separate binary tool
   - No pure-Python DWG reader exists

3. **Complexity**: Even with DXF (which ezdxf can read), extracting title blocks is hard:
   - No standard title block format in CAD
   - Text can be in blocks, attributes, or plain text entities
   - Need to know exact layout/coordinate system
   - Multiple coordinate systems (model space, paper space, layouts)

4. **Performance**: Opening DWG files (even via conversion) is significantly slower than 
   PDF text extraction.

### Recommended Approach:

**Don't parse DWG files directly.** Instead:

1. **Detect pairing issues** (what we're implementing here):
   - Flag when PDF and DWG names don't match
   - User can manually fix naming
   
2. **Require PDFs**: 
   - PDFs are the "published" format for review/approval
   - DWG is source file, PDF is deliverable
   - Only validate PDFs
   
3. **Optional DXF Support** (future):
   - If users can export DXF alongside PDF, we could support it
   - Use ezdxf library to read DXF files
   - Still complex but more feasible than DWG

4. **Automated Checks**:
   - Ensure DWG exists for each PDF (pairing)
   - Ensure names match conventions
   - Check file dates (DWG should be older or same age as PDF)
   - But don't read DWG contents

### Conclusion:

For this tool, **detecting DWG/PDF pairing issues and naming mismatches** provides 90% 
of the value with 10% of the complexity. Actual DWG title block reading would be a 
separate major project requiring external tools or AutoCAD COM automation.
"""
