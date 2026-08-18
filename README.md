# Drawing title-block QA

Drop **TBCheck.exe** into a folder of construction drawing PDFs and double-click. It checks every PDF in that folder and writes an Excel report next to the exe.

This follows the same “run where it sits” pattern as [mbs-file-tools](https://github.com/Optimodo/mbs-file-tools).

For each PDF it:

1. Parses an **ISO 19650** document reference (and optional title / revision) from the filename.
2. Detects which configured **title-block layout** the sheet uses.
3. Reads document reference, title, and revision from the title block (vector text).
4. Writes **TBCheckReport.xlsx** (or `TBCheckReport-1.xlsx`, `-2.xlsx`, … if a report already exists).

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

The workbook has four sheets:

- **Summary** — counts by status
- **All documents** — every PDF
- **Needs attention** — mismatches, incomplete reads, undetected layouts, parse errors
- **Matches** — filename and title block agree

| Status | Meaning |
| --- | --- |
| `MATCH` | Required fields agree |
| `MISMATCH` | Filename and title block disagree |
| `INCOMPLETE` | Layout found, but a required field was missing |
| `UNDETECTED` | No configured layout scored high enough |
| `FILENAME_PARSE_ERROR` | Filename is not ISO 19650 |
| `ERROR` | PDF could not be read |

Document reference and revision are **required** by default. Title is compared only when it appears in **both** the filename and the title block.

## Tests and Linux freeze check

```bash
pytest
pip install -e ".[build]"
python scripts/build_exe.py
```

On Linux that produces `dist/TBCheck` (not a Windows `.exe`). Build the Windows exe with `build_exe.bat` on Windows.
