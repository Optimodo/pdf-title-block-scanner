# Contributing to Drawing QA

Thank you for your interest in contributing to the Drawing QA project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Adding Title-Block Layouts](#adding-title-block-layouts)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/drawing-qa.git
   cd drawing-qa
   ```
3. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11 or later
- Git

### Installation

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install the package in development mode with all dependencies:
   ```bash
   pip install -e ".[dev,build]"
   ```

3. Install pre-commit hooks (recommended):
   ```bash
   pre-commit install
   ```

   This will automatically run linting and formatting checks before each commit.

## Running Tests

### Run all tests:
```bash
pytest
```

### Run tests with coverage:
```bash
pytest --cov=drawing_qa --cov-report=term-missing --cov-report=html
```

View the HTML coverage report:
```bash
open htmlcov/index.html  # On macOS
# Or navigate to htmlcov/index.html in your browser
```

### Run specific test file:
```bash
pytest tests/test_checker.py
```

### Run with verbose output:
```bash
pytest -v
```

## Code Style

This project uses:

- **Ruff** for linting and formatting (replaces black, isort, flake8)
- **MyPy** for static type checking
- **Pre-commit** hooks for automated checks

### Manual linting and formatting:

```bash
# Check code style
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Run type checking
mypy src/
```

### Code Style Guidelines

- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use pathlib.Path for file paths (not strings)
- Use dataclasses for data structures
- Follow PEP 8 naming conventions:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Docstrings

Use Google-style docstrings for public functions:

```python
def check_pdf(path: Path, config: AppConfig) -> DocumentResult:
    """Check a single PDF against ISO 19650 standards.
    
    Args:
        path: Path to the PDF file to check
        config: Application configuration including title-block layouts
        
    Returns:
        DocumentResult containing filename parsing, title-block extraction,
        comparison results, and status
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
    """
```

## Adding Title-Block Layouts

To add support for a new title-block layout:

### 1. Inspect an example PDF:

```bash
drawing-qa inspect path/to/example.pdf --debug-dir debug
```

This creates cropped images and dumps text coordinates in the `debug/` folder.

### 2. Create a YAML configuration:

Create a new file in `src/drawing_qa/default_config/title_blocks/your_layout.yaml`:

```yaml
id: your_layout
name: "Your Layout Name"

# Region as fractions of page width/height (0.0 to 1.0, origin at top-left)
region:
  left: 0.75
  top: 0.85
  right: 1.0
  bottom: 1.0

# Text labels that uniquely identify this layout
anchors:
  - "DRAWING NO"
  - "REV"
  - "DATE"

# At least one group of anchors must be present
required_anchor_groups:
  - ["DRAWING NO", "REV"]
  - ["DRAWING NUMBER", "REVISION"]

# Minimum detection score (0.0 to 1.0)
min_score: 0.7

# Field extraction configuration
fields:
  document_reference:
    labels: ["DRAWING NO", "DWG NO"]
    direction: auto  # Try right, then below
  
  title:
    labels: ["TITLE", "DRAWING TITLE"]
    direction: below
  
  revision:
    labels: ["REV", "REVISION"]
    direction: right
  
  suitability:
    labels: ["STATUS", "SUITABILITY"]
    direction: right
  
  date:
    labels: ["DATE"]
    direction: right

# Revision history table configuration
history:
  expand_left: 0.25    # Expand search region left
  expand_right: 0.0
  expand_top: 0.05     # Expand search region up
  expand_bottom: 0.0
  min_rows: 2          # Minimum rows to consider it a history table
```

### 3. Test your layout:

```bash
# Check a PDF with your new layout
drawing-qa check path/to/pdf-folder --output test-report.xlsx

# Verify detection
pytest tests/test_checker.py -v
```

### 4. Add a test fixture:

Add a test PDF generator in `tests/pdf_fixtures.py` and a test in `tests/test_checker.py`.

## Submitting Changes

### Before submitting:

1. Ensure all tests pass: `pytest`
2. Check code style: `ruff check .`
3. Run type checking: `mypy src/`
4. Update CHANGELOG.md under `[Unreleased]`
5. Add tests for new functionality

### Pull Request Process:

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub with:
   - Clear description of the changes
   - Link to any related issues
   - Screenshots (if UI changes)
   - Test results

3. Address review feedback

4. Once approved, the maintainers will merge your PR

### Commit Message Guidelines

Use clear, descriptive commit messages:

- Start with a verb in present tense: "Add", "Fix", "Update", etc.
- Keep the first line under 72 characters
- Add details in the body if needed

Examples:
```
Add support for custom date formats in history tables

Fix crash when PDF has no text layer

Update documentation for layout configuration
```

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md:
   - Move `[Unreleased]` changes to new version section
   - Add release date
3. Create and push git tag:
   ```bash
   git tag -a v0.2.0 -m "Release version 0.2.0"
   git push origin v0.2.0
   ```
4. Build and test the Windows executable:
   ```bash
   build_exe.bat
   ```
5. Create GitHub release with:
   - Changelog for this version
   - Attached TBCheck.exe

## Questions?

- Open an issue for bugs or feature requests
- Discussions for general questions
- Email the maintainers for security issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
