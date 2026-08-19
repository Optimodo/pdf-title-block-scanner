# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD workflow for automated testing
- Support for Python 3.11 and 3.12
- Test coverage reporting with pytest-cov
- Ruff for linting and code formatting
- MyPy for static type checking
- Pre-commit hooks configuration
- EditorConfig for consistent coding style
- Dependabot for automated dependency updates
- LICENSE file (MIT)
- CONTRIBUTING.md with development guidelines
- CHANGELOG.md for tracking changes
- IMPROVEMENTS.md with comprehensive improvement recommendations

## [0.1.0] - 2026-08-19

### Added
- Initial release of TBCheck - Drawing title-block QA tool
- ISO 19650 document reference parsing from filenames
- Title-block layout detection system with three default layouts:
  - `bottom_right`: Title block in bottom-right corner
  - `bottom_strip`: Title block as bottom strip
  - `mbs_right`: Right-hand title block
- Five-field extraction from title blocks:
  - Document reference
  - Title
  - Revision
  - Purpose of issue/suitability
  - Date
- Revision history table parsing
- Excel report generation with:
  - Summary sheet with confidence and status counts
  - Review needed sheet for mismatches and issues
  - High confidence sheet for verified matches
  - All documents sheet with complete data
  - Preview images showing extracted fields
- Standalone Windows executable build system
- CLI with `check` and `inspect` commands
- Configurable title-block layouts via YAML
- Support for non-ISO filenames (still extracts title-block fields)
- Comprehensive test suite with PDF generation fixtures
- Status tracking:
  - MATCH: Filename and title block agree
  - MISMATCH: Discrepancies found
  - HISTORY_MISMATCH: History table disagrees with current revision
  - INCOMPLETE: Missing required fields
  - UNDETECTED: No layout detected
  - FILENAME_PARSE_ERROR: Non-ISO filename
  - ERROR: PDF read failure

### Dependencies
- pymupdf>=1.24.0 for PDF processing
- openpyxl>=3.1.0 for Excel report generation
- pyyaml>=6.0 for configuration files
- pillow>=10.0 for image processing
- pyinstaller>=6.0 for executable building
