# Drawing title-block QA

CLI tool that checks construction drawing PDFs against their filenames.

For each PDF it:

1. Parses an **ISO 19650** document reference (and optional title / revision) from the filename.
2. Detects which configured **title-block layout** the sheet uses.
3. Reads document reference, title, and revision from the title block (vector text).
4. Writes an **Excel report** of matches and mismatches.

OCR for scanned PDFs is out of scope for this first version. Sheets need a selectable CAD text layer.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Check a folder of PDFs
drawing-qa check path/to/drawings --output reports/titleblock-qa.xlsx

# Check one file
drawing-qa check path/to/ABC-WXY-ZZ-00-DR-A-0001-P01.pdf

# Dump text + a cropped image for each configured title-block region
drawing-qa inspect path/to/drawing.pdf --debug-dir debug
```

`check` exits `0` when every document is a `MATCH`, and `1` when anything needs attention.

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

Revision pattern and field count are set in [`config/settings.yaml`](config/settings.yaml).

## Title-block layouts

Layouts live in [`config/title_blocks/`](config/title_blocks/). Add one YAML file per style. The checker scores every layout against the text in that layout's page region and uses the best match.

Typical workflow for a new style:

1. Run `drawing-qa inspect some.pdf` and look at the cropped PNGs plus dumped coordinates.
2. Copy an existing YAML file.
3. Adjust `region` (fractions of page width/height, origin at top-left).
4. Set `required_anchor_groups` to labels that uniquely identify the style (`DRAWING NO`, `REV`, …).
5. Map each field to the printed heading via `labels`. `direction: auto` tries to the right of the heading, then below it.
6. Optionally pin a field with `clip` boxes instead of labels (`relative_to: region` or `page`).

`inspect` is the configuration aid; you do not have to guess coordinates blindly.

## Report

The workbook has four sheets:

- **Summary** — counts by status
- **All documents** — every PDF
- **Needs attention** — mismatches, incomplete reads, undetected layouts, parse errors
- **Matches** — filename and title block agree

Statuses:

| Status | Meaning |
| --- | --- |
| `MATCH` | Required fields agree |
| `MISMATCH` | Filename and title block disagree |
| `INCOMPLETE` | Layout found, but a required field was missing |
| `UNDETECTED` | No configured layout scored high enough |
| `FILENAME_PARSE_ERROR` | Filename is not ISO 19650 |
| `ERROR` | PDF could not be read |

Document reference and revision are **required** by default. Title is compared only when it appears in **both** the filename and the title block.

## Tests

```bash
pytest
```

Tests build small synthetic CAD-style PDFs; no live drawing set is required.
