# Drawing title-block QA

[![CI](https://github.com/Optimodo/drawing-qa/workflows/CI/badge.svg)](https://github.com/Optimodo/drawing-qa/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Drop **TBCheck.exe** into a folder of construction drawing PDFs and double-click. It checks every PDF in that folder and writes an Excel report next to the exe.

This follows the same “run where it sits” pattern as [mbs-file-tools](https://github.com/Optimodo/mbs-file-tools).

For each PDF it:

1. Parses an **ISO 19650** document reference (and optional title / revision) from the filename when present.
2. Detects which configured **title-block layout** the sheet uses.
3. Reads five current attributes from the title block (not the revision-history table): document reference, title, revision, purpose of issue / suitability, and date.
4. Parses the **revision history** table separately, takes only the **latest** row, and checks it against the current title-block revision / date / status.
5. Writes **TBCheckReport.xlsx** with a summary, a Review needed tab, a High confidence tab, and tight screenshots of the five detected fields.

Non-ISO filenames are still processed: title-block values are extracted and shown in the report even when the filename cannot supply a document reference.

OCR for scanned PDFs is out of scope for this version. Sheets need a selectable CAD text layer.

## Run the standalone exe (Windows)

1. Build it on a Windows machine (Python 3.11+):

   ```bat
   pip install -e ".[dev,build]"
   build_exe.bat
   ```

   The file lands in `dist\TBCheck.exe`.

2. Copy `TBCheck.exe` into the folder that contains the drawing PDFs.
3. Double-click. A console window lists each file, then waits for Enter.
4. Open `TBCheckReport.xlsx` in the same folder.

Optional: copy a `config\` folder next to the exe to override bundled title-block layouts. If that folder is missing, the exe uses the layouts baked into it.

The exe only looks at PDFs in **that folder**, not subfolders. It does not rename files and does not use the network.

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Check every PDF in the current folder
python tbcheck.py --no-pause

# Or use the CLI
drawing-qa check path/to/drawings --output reports/titleblock-qa.xlsx
drawing-qa inspect path/to/drawing.pdf --debug-dir debug
```

`check` / a double-click run exits `0` when every document is a `MATCH`, and `1` when anything needs attention.

## Filename convention

Expected stem (ISO 19650-2, seven hyphen-separated fields):

```
Project-Originator-Volume-Level-Type-Role-Number
```

Optional suffix for title and/or revision:

| Example | Document reference | Title | Revision |
| --- | --- | --- | --- |
| `ABC-WXY-ZZ-00-DR-A-0001-P01.pdf` | `ABC-WXY-ZZ-00-DR-A-0001` | — | `P01` |
| `ABC-WXY-ZZ-00-DR-A-0001_Ground Floor GA_C02.pdf` | `ABC-WXY-ZZ-00-DR-A-0001` | `Ground Floor GA` | `C02` |
| `ABC-WXY-ZZ-00-DR-A-0001.pdf` | `ABC-WXY-ZZ-00-DR-A-0001` | — | — |

Revision pattern and field count are set in [`src/drawing_qa/default_config/settings.yaml`](src/drawing_qa/default_config/settings.yaml).

## Title-block layouts

Default layouts live in [`src/drawing_qa/default_config/title_blocks/`](src/drawing_qa/default_config/title_blocks/). To customize a deployed copy, put YAML files in `config\title_blocks\` next to the exe (and include `config\settings.yaml`).

Typical workflow for a new style:

1. Run `drawing-qa inspect some.pdf` and look at the cropped PNGs plus dumped coordinates.
2. Copy an existing YAML file.
3. Adjust `region` (fractions of page width/height, origin at top-left).
4. Set `required_anchor_groups` to labels that uniquely identify the style (`DRAWING NO`, `REV`, …).
5. Map each field to the printed heading via `labels`. `direction: auto` tries to the right of the heading, then below it.

## Report

The workbook has four sheets. Start on **Review needed**.

- **Summary** — confidence counts, status counts, and what each status means
- **Review needed** — mismatches, history disagreements, incomplete reads, undetected layouts, parse errors
- **High confidence** — filename, current title block, and latest history row all agree
- **All documents** — every PDF

Each data row is medium height and includes a **preview strip**: five tight crops (doc ref, title, revision, suitability, date) — not the whole title block.

| Status | Meaning |
| --- | --- |
| `MATCH` | Filename agrees with the current title block; latest history row matches current |
| `MISMATCH` | Filename disagrees with the current title-block values |
| `HISTORY_MISMATCH` | Current title block disagrees with the latest revision-history row |
| `INCOMPLETE` | Layout found, but a required field was missing |
| `UNDETECTED` | No configured layout scored high enough |
| `FILENAME_PARSE_ERROR` | Filename is not ISO 19650; title-block values are still reported for manual review |
| `ERROR` | PDF could not be read |

Document reference and revision are **required** when the filename is ISO 19650. Title, suitability, and date are compared when both sides have a value. Older history rows are never compared to the current revision.

## Development

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,build]"
pre-commit install
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=drawing_qa --cov-report=term-missing

# Run linting
ruff check .

# Run type checking
mypy src/
```

### Building

```bash
# Build executable (produces dist/TBCheck or dist/TBCheck.exe)
python scripts/build_exe.py

# On Windows, use the batch script
build_exe.bat
```

On Linux this produces `dist/TBCheck` (not a Windows `.exe`). Build the Windows exe with `build_exe.bat` on Windows.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

[MIT License](LICENSE)
