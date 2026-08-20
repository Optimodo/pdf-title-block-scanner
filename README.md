# Drawing title-block QA

Drop **TBCheck.exe** or **TBCheckRename.exe** into a folder of construction drawing PDFs and double-click. Both scan every PDF in that folder and write **TBCheckReport.xlsx** next to the exe.

This follows the same “run where it sits” pattern as [mbs-file-tools](https://github.com/Optimodo/mbs-file-tools). Use that toolkit to strip names down to the document reference only. Use **TBCheckRename** in this project when you want names built from the **title-block** document reference, title, and revision (that needs the PDF scan).

| Exe | Report | Rename |
| --- | --- | --- |
| **TBCheck.exe** | Yes | Optional. If the filename document reference disagrees with the title block, you are prompted to fix it. The rest of the existing name is kept. |
| **TBCheckRename.exe** | Yes | Automatic. Every PDF with a readable title-block document reference is renamed to `{doc-ref}_{title}_{revision}.pdf`. No prompt. |

The report always keeps **File (as scanned)** as the name at the start of the run. After a rename, **New filename** and **Rename result** show what is on disk (or why a rename was skipped). Notes also record `Renamed from … to …`.

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
   python scripts/build_exe.py
   ```

   That produces `dist\TBCheck.exe` and `dist\TBCheckRename.exe`.

2. Copy the exe you want into the folder that contains the drawing PDFs.
3. Double-click. A console window lists each file, then waits for Enter.
4. **TBCheck:** if a filename document reference does not match the title block, you can preview and apply a fix (paired DWG files are renamed the same way).
5. **TBCheckRename:** files are renamed automatically to `{doc-ref}_{title}_{revision}` from the title block; the Excel report lists original names, new names, and rename results.
6. Open `TBCheckReport.xlsx` in the same folder to review results.

Optional: copy a `config\` folder next to the exe to override bundled title-block layouts and the purpose-of-issue whitelist (`suitability.yaml`). If that folder is missing, the exe uses the files baked into it.

The exe looks at PDFs in **that folder**, not subfolders (unless `--recursive` is specified). It does not use the network.

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Check every PDF in the current folder
python tbcheck.py --no-pause

# Auto-rename to doc-ref_title_revision from the title block
python tbcheck_rename.py --no-pause

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

Default layouts live in [`src/drawing_qa/default_config/title_blocks/`](src/drawing_qa/default_config/title_blocks/). The accepted purpose-of-issue / suitability list is [`src/drawing_qa/default_config/suitability.yaml`](src/drawing_qa/default_config/suitability.yaml) (ISO 19650-2 UK NA.1 as a starting point). To customize a deployed copy, put YAML files in `config\title_blocks\` next to the exe and include `config\settings.yaml` plus `config\suitability.yaml`.

Typical workflow for a new style:

1. Run `drawing-qa inspect some.pdf` and look at the cropped PNGs plus dumped coordinates.
2. Copy an existing YAML file.
3. Adjust `region` (fractions of page width/height, origin at top-left).
4. Set `required_anchor_groups` to labels that uniquely identify the style (`DRAWING NO`, `REV`, …).
5. Map each field to the printed heading via `labels`. `direction: auto` tries to the right of the heading, then below it.

## Report

The workbook has four sheets. Start on **Review needed**.

- **Summary** — confidence counts, status counts, rename counts when files were renamed, and what each status means
- **Review needed** — mismatches, history disagreements, incomplete reads, undetected layouts, parse errors
- **High confidence** — filename, current title block, and latest history row all agree
- **All documents** — every PDF

Data rows include **File (as scanned)** (name at the start of the run), **New filename**, and **Rename result** so the workbook still makes sense after files have been renamed on disk.

Each data row is medium height and includes a **preview strip**: five tight crops (doc ref, title, revision, suitability, date) — not the whole title block.

| Status | Meaning |
| --- | --- |
| `MATCH` | Filename agrees with the current title block; latest history row matches current |
| `MISMATCH` | Filename disagrees with the current title-block values |
| `HISTORY_MISMATCH` | Current title block disagrees with the latest revision-history row |
| `INCOMPLETE` | Layout found, but a required field was missing |
| `UNDETECTED` | No configured layout scored high enough |
| `FILENAME_PARSE_ERROR` | Filename is not ISO 19650; title-block values are still reported for manual review |
| `SPELLING_ERROR` | Possible spelling error in the title |
| `DATE_REGRESSION` | Later revision in history has an earlier date |
| `DUPLICATE_REFERENCE` | More than one PDF has the same document reference |
| `SUITABILITY_ERROR` | Purpose of issue / suitability is not in `suitability.yaml` |
| `ERROR` | PDF could not be read |
| `MULTIPLE_ISSUES` | More than one issue; column A lists them all |

Document reference and revision are **required** when the filename is ISO 19650. Title, suitability, and date are compared when both sides have a value. Older history rows are never compared to the current revision.

## Tests and Linux freeze check

```bash
pytest
pip install -e ".[build]"
python scripts/build_exe.py
```

On Linux that produces `dist/TBCheck` and `dist/TBCheckRename` (not Windows `.exe` files). Build the Windows exes with `build_exe.bat` on Windows.
