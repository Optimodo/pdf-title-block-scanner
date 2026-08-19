# Project Improvement Recommendations

## Executive Summary

This document outlines actionable improvements for the Drawing QA project. The project is well-structured with good test coverage (~368 test lines for ~2566 source lines). Key areas for enhancement include CI/CD automation, code quality tooling, documentation, and developer experience.

## 1. CI/CD and Automation

### Missing GitHub Actions Workflow

**Priority: HIGH**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ['3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev,build]"
    - name: Run tests
      run: pytest --verbose
    - name: Verify build
      run: python scripts/build_exe.py

  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install linting tools
      run: pip install ruff mypy
    - name: Run ruff
      run: ruff check .
    - name: Run mypy
      run: mypy src/
```

**Benefits:**
- Automated testing on every push/PR
- Multi-platform validation (Linux + Windows)
- Multi-version Python support
- Early detection of issues

---

## 2. Code Quality Tools

### 2.1 Add Ruff for Linting and Formatting

**Priority: HIGH**

Add to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez
    "PIE",    # flake8-pie
    "PT",     # flake8-pytest-style
    "RSE",    # flake8-raise
    "RET",    # flake8-return
    "SIM",    # flake8-simplify
    "PTH",    # flake8-use-pathlib
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "BLE001", # already in use with noqa
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["PT011", "PTH"]
```

Update dev dependencies in `pyproject.toml`:

```toml
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "ruff>=0.5.0",
    "mypy>=1.10",
]
```

**Benefits:**
- Fast linting and formatting (10-100x faster than flake8/black)
- Consistent code style
- Auto-fix capabilities
- Replaces multiple tools (isort, black, flake8)

---

### 2.2 Add MyPy for Type Checking

**Priority: MEDIUM**

Add to `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
disallow_incomplete_defs = false
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[[tool.mypy.overrides]]
module = "pymupdf.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "openpyxl.*"
ignore_missing_imports = true
```

**Benefits:**
- Catch type-related bugs early
- Better IDE autocomplete
- Improved code documentation
- Gradual adoption (not strict initially)

---

## 3. Testing Enhancements

### 3.1 Add Test Coverage Reporting

**Priority: MEDIUM**

Update `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "--cov=drawing_qa",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
]

[tool.coverage.run]
branch = true
source = ["src/drawing_qa"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

**Benefits:**
- Identify untested code paths
- Track coverage trends
- Integration with GitHub Actions

---

### 3.2 Add Integration Test Fixtures

**Priority: LOW**

Create `tests/test_integration.py` for end-to-end scenarios:
- Test full workflow from PDF to Excel report
- Test error recovery scenarios
- Test with malformed PDFs
- Performance benchmarks for large batches

---

## 4. Documentation Improvements

### 4.1 Add CONTRIBUTING.md

**Priority: MEDIUM**

Create a contributor guide covering:
- Development setup
- Running tests
- Code style guidelines
- How to add new title-block layouts
- Pull request process

---

### 4.2 Add CHANGELOG.md

**Priority: MEDIUM**

Track changes in a structured format (Keep a Changelog format):

```markdown
# Changelog

## [Unreleased]

## [0.1.0] - 2026-08-XX
### Added
- Initial release
- ISO 19650 filename parsing
- Three title-block layouts (bottom_right, bottom_strip, mbs_right)
- Excel report generation with preview images
- Revision history validation
```

---

### 4.3 Enhance Docstrings

**Priority: LOW**

Add comprehensive docstrings to public functions, especially:
- `checker.check_pdf()` - main entry point
- `detect.extract_titleblock()` - core extraction logic
- `compare.compare_document()` - comparison logic

Example:

```python
def check_pdf(path: Path, config: AppConfig) -> DocumentResult:
    """Check a single PDF against ISO 19650 standards.
    
    Args:
        path: Path to the PDF file to check
        config: Application configuration including title-block layouts
        
    Returns:
        DocumentResult containing filename parsing, title-block extraction,
        comparison results, and status (MATCH/MISMATCH/etc.)
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        
    Example:
        >>> config = load_config(Path("config/"))
        >>> result = check_pdf(Path("drawing.pdf"), config)
        >>> print(result.status)
        CheckStatus.MATCH
    """
```

---

## 5. Dependency Management

### 5.1 Add requirements.txt Files

**Priority: LOW**

Generate lockfiles for reproducible builds:

```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt
pip-compile --extra dev pyproject.toml -o requirements-dev.txt
```

**Benefits:**
- Reproducible builds
- Faster CI installs
- Pin transitive dependencies

---

### 5.2 Add Dependabot Configuration

**Priority: LOW**

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

---

## 6. Error Handling and Logging

### 6.1 Add Structured Logging

**Priority: MEDIUM**

Replace print statements with proper logging:

```python
import logging

logger = logging.getLogger(__name__)

# In cli.py
def run_folder_check(...):
    logger.info("Starting title-block QA check", extra={
        "folder": str(folder),
        "pdf_count": len(pdfs)
    })
```

Add logging configuration:

```python
# In cli.py
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("tbcheck.log")
        ]
    )
```

**Benefits:**
- Better debugging
- Log files for issue investigation
- Structured error reporting

---

### 6.2 Add Custom Exception Classes

**Priority: LOW**

Create `src/drawing_qa/exceptions.py`:

```python
class DrawingQAError(Exception):
    """Base exception for drawing-qa."""

class ConfigError(DrawingQAError):
    """Configuration loading error."""

class PDFReadError(DrawingQAError):
    """PDF file reading error."""

class LayoutDetectionError(DrawingQAError):
    """Title-block layout detection error."""
```

---

## 7. Performance Optimizations

### 7.1 Add Progress Bar for Large Batches

**Priority: LOW**

Add `tqdm` for better user feedback:

```toml
dependencies = [
    "pymupdf>=1.24.0",
    "openpyxl>=3.1.0",
    "pyyaml>=6.0",
    "pillow>=10.0",
    "tqdm>=4.66.0",
]
```

```python
from tqdm import tqdm

for path in tqdm(pdfs, desc="Processing PDFs"):
    result = check_pdf(path, config)
```

---

### 7.2 Add Parallel Processing Option

**Priority: LOW**

Add multiprocessing for large batches:

```python
from concurrent.futures import ProcessPoolExecutor

def check_paths_parallel(paths: list[Path], config: AppConfig, workers: int = 4) -> list[DocumentResult]:
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(check_pdf, path, config) for path in paths]
        return [f.result() for f in futures]
```

---

## 8. Security Enhancements

### 8.1 Add Security Scanning

**Priority: MEDIUM**

Add to `.github/workflows/security.yml`:

```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - name: Run safety check
      run: |
        pip install safety
        safety check --json
    - name: Run bandit
      run: |
        pip install bandit
        bandit -r src/
```

---

## 9. User Experience Improvements

### 9.1 Add Validation Mode

**Priority: LOW**

Add a `validate` command to check config files without processing PDFs:

```python
def cmd_validate(args: argparse.Namespace) -> int:
    """Validate configuration files."""
    try:
        config = load_config(args.config_dir)
        print(f"✓ Configuration valid: {len(config.layouts)} layouts loaded")
        return 0
    except Exception as exc:
        print(f"✗ Configuration error: {exc}")
        return 1
```

---

### 9.2 Add Dry-Run Mode

**Priority: LOW**

Add `--dry-run` flag to preview what would be checked without writing reports.

---

### 9.3 Add JSON Output Format

**Priority: LOW**

Support machine-readable output:

```python
check.add_argument(
    "--format",
    choices=["excel", "json"],
    default="excel",
    help="Output format"
)
```

---

## 10. Project Metadata

### 10.1 Add LICENSE File

**Priority: HIGH**

Create `LICENSE` file (currently only mentioned in pyproject.toml):

```
MIT License

Copyright (c) 2026 [Your Organization]

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

---

### 10.2 Add .editorconfig

**Priority: LOW**

Create `.editorconfig` for consistent editor settings:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

---

### 10.3 Add pre-commit Hooks

**Priority: MEDIUM**

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Install with:
```bash
pip install pre-commit
pre-commit install
```

---

## Implementation Priority

### Phase 1 (Immediate - High Impact)
1. Add GitHub Actions CI/CD workflow
2. Add LICENSE file
3. Add Ruff linting and formatting
4. Add test coverage reporting

### Phase 2 (Short-term - Developer Experience)
5. Add pre-commit hooks
6. Add MyPy type checking
7. Add structured logging
8. Add CONTRIBUTING.md and CHANGELOG.md

### Phase 3 (Medium-term - Quality)
9. Add security scanning
10. Enhanced docstrings
11. Add Dependabot
12. Custom exception classes

### Phase 4 (Long-term - Features)
13. Parallel processing
14. Progress bars
15. JSON output format
16. Validation and dry-run modes

---

## Metrics to Track

- **Test Coverage**: Target 80%+
- **Build Success Rate**: Target 100% on main
- **Code Quality**: Ruff violations = 0
- **Type Coverage**: Gradual increase with MyPy
- **Documentation**: All public APIs documented

---

## Conclusion

These improvements will enhance:
- **Reliability**: Automated testing and CI/CD
- **Maintainability**: Consistent code style and documentation
- **Security**: Dependency scanning and updates
- **Developer Experience**: Pre-commit hooks and clear guidelines
- **User Experience**: Better error messages and progress feedback

The project already has a solid foundation with good separation of concerns, comprehensive tests, and clear documentation. These improvements will make it production-ready and easier for contributors to work with.
