# Flexible Rename Modes Implementation Summary

## Overview

This implementation adds flexible file renaming capabilities to the Drawing QA tool, allowing users to choose between renaming files with just the document reference (for portal uploads) or including full details (title and revision) for comprehensive file standardization.

## Key Requirements Addressed

1. **Standard Tool (TBCheck.exe)**
   - Interactive rename prompts when mismatches are detected
   - Rename to document reference only (no title or revision)
   - Format: `ABC-XYZ-ZZ-00-DR-A-0001.pdf`
   - Suitable for uploading to client document portals

2. **Rename Variant (TBCheckRename.exe)**
   - Automatic rename without user prompts
   - Include document reference, title, and revision
   - Format: `ABC-XYZ-ZZ-00-DR-A-0001_Floor Plan_P01.pdf`
   - Suitable for batch standardizing project file naming

## Implementation Changes

### Core Functionality

#### 1. `src/drawing_qa/validation.py`
Modified `suggest_filename()` to accept optional parameters:
```python
def suggest_filename(
    result: DocumentResult,
    include_title: bool = False,
    include_revision: bool = False,
) -> str | None:
```

**Behavior:**
- Default: Only document reference
- With `include_title=True`: Adds title after underscore
- With `include_revision=True`: Adds revision (dash separator for short codes, underscore otherwise)
- Both flags: Includes all three components

#### 2. `src/drawing_qa/checker.py`
Updated `check_paths()` to pass rename preferences:
```python
def check_paths(
    paths: list[Path],
    config: AppConfig,
    suggest_title: bool = False,
    suggest_revision: bool = False,
) -> list[DocumentResult]:
```

#### 3. `src/drawing_qa/cli.py`
Added three new command-line flags:
- `--auto-rename`: Skip user prompts and rename automatically
- `--include-title`: Include title in renamed filenames
- `--include-revision`: Include revision in renamed filenames

Modified rename logic to support two modes:
- **Interactive mode** (`progress=True`): Offers rename prompt to user
- **Auto-rename mode** (`auto_rename=True`): Renames without prompts

### New Entry Points

#### 1. `src/drawing_qa/cli_rename.py`
New module providing the entry point for the rename variant:
```python
def main(argv: list[str] | None = None) -> int:
    args = ["--auto-rename", "--include-title", "--include-revision"]
    args.extend(argv or sys.argv[1:])
    return cli_main(args)
```

#### 2. `tbcheck_rename.py`
Root-level script for the rename executable:
```python
from drawing_qa.cli_rename import main

if __name__ == "__main__":
    sys.exit(main())
```

#### 3. `scripts/TBCheckRename.py`
Alternative entry point script (for flexibility in build process).

### Build System Updates

#### `scripts/build_exe.py`
Completely refactored to build both executables:
- Extracted `build_executable()` function for reusability
- Builds `TBCheck.exe` from `tbcheck.py`
- Builds `TBCheckRename.exe` from `tbcheck_rename.py`
- Added `spellchecker` to hidden imports
- Both executables share the same bundled config

#### `pyproject.toml`
Added new script entry point:
```toml
[project.scripts]
drawing-qa = "drawing_qa.cli:main"
tbcheck = "drawing_qa.cli:main"
tbcheck-rename = "drawing_qa.cli_rename:main"
```

### Testing

#### `tests/test_rename_modes.py`
Comprehensive test suite covering:
1. Document reference only (default)
2. With title
3. With revision
4. With both title and revision
5. Missing title handling
6. Missing revision handling

All tests verify correct filename generation for each mode.

#### Updated Tests
`tests/test_validation.py::test_filename_suggestion_for_mismatch` was enhanced to test all four modes.

## Usage Examples

### Command Line

```bash
# Standard interactive mode (doc ref only)
drawing-qa check /path/to/drawings

# Auto-rename with doc ref only
drawing-qa check /path/to/drawings --auto-rename

# Auto-rename with title
drawing-qa check /path/to/drawings --auto-rename --include-title

# Auto-rename with title and revision (full details)
drawing-qa check /path/to/drawings --auto-rename --include-title --include-revision

# Or use the rename variant directly
tbcheck-rename /path/to/drawings
```

### Executable Behavior

**TBCheck.exe:**
1. Runs QA checks
2. Generates Excel report
3. If mismatches found, prints summary
4. Prompts: "Rename files? (yes/no/preview)"
5. Renames to document reference only

**TBCheckRename.exe:**
1. Runs QA checks
2. Generates Excel report
3. If mismatches found, prints summary
4. Automatically renames to full format (no prompt)
5. Includes document reference, title, and revision

## Rename Format Examples

### Document Reference Only (TBCheck.exe default)
- Input: `Wrong-Name-Here.pdf`
- Title Block: Doc Ref = `ABC-XYZ-ZZ-00-DR-A-0001`, Title = "Floor Plan", Rev = "P01"
- Output: `ABC-XYZ-ZZ-00-DR-A-0001.pdf`

### Full Details (TBCheckRename.exe)
- Input: `Wrong-Name-Here.pdf`
- Title Block: Doc Ref = `ABC-XYZ-ZZ-00-DR-A-0001`, Title = "Floor Plan", Rev = "P01"
- Output: `ABC-XYZ-ZZ-00-DR-A-0001_Floor Plan_P01.pdf`

### With Title Only
- Input: `Wrong-Name-Here.pdf`
- Title Block: Doc Ref = `ABC-XYZ-ZZ-00-DR-A-0001`, Title = "Floor Plan", Rev = "P01"
- Output: `ABC-XYZ-ZZ-00-DR-A-0001_Floor Plan.pdf`

### With Revision Only
- Input: `Wrong-Name-Here.pdf`
- Title Block: Doc Ref = `ABC-XYZ-ZZ-00-DR-A-0001`, Title = "Floor Plan", Rev = "P01"
- Output: `ABC-XYZ-ZZ-00-DR-A-0001-P01.pdf`

## Benefits

1. **Portal Compliance**: Doc ref only mode ensures files meet portal naming requirements
2. **Human Readability**: Full details mode makes files self-descriptive
3. **Flexibility**: CLI flags allow any combination of components
4. **Automation**: Auto-rename mode enables batch processing
5. **Safety**: Interactive mode prevents accidental renames
6. **DWG Support**: Both modes rename paired DWG files automatically

## Technical Notes

- Renaming respects paired DWG files (both get renamed together)
- Special characters in titles are sanitized (/, \ converted to -)
- Whitespace is normalized
- Short revision codes use dash separator, longer values use underscore
- If title/revision are requested but missing from title block, they're skipped gracefully

## Files Modified

- `src/drawing_qa/validation.py`
- `src/drawing_qa/checker.py`
- `src/drawing_qa/cli.py`
- `scripts/build_exe.py`
- `pyproject.toml`
- `README.md`

## Files Created

- `src/drawing_qa/cli_rename.py`
- `tbcheck_rename.py`
- `scripts/TBCheckRename.py`
- `tests/test_rename_modes.py`
- `RENAME_MODES_SUMMARY.md` (this file)

## Test Results

All 71 tests pass, including:
- 6 new tests for rename modes
- Updated validation tests
- All existing tests remain compatible

## Documentation Updates

- README now documents both executables
- CLI flag documentation added
- Usage examples for different scenarios
- Build instructions updated for both executables
