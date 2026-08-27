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
5. Writes an Excel report with a summary, a Designer actions tab (for sending to CAD), a Review needed tab with previews, a High confidence tab, and tight screenshots of the five detected fields.
6. Optionally cross-checks a client-portal **document list** in the same folder (revision one-up, and title if both sides have one). If none is found, this step is skipped.

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
6. Open the `{project}_{ddmmyy}.xlsx` report in the same folder to review results.

Optional: copy a `config\` folder next to the exe to override bundled title-block layouts, the purpose-of-issue whitelist (`suitability.yaml`), and portal document-list column names (`document_lists.yaml`). If that folder is missing, the exe uses the files baked into it.

The exe looks at PDFs in **that folder**, not subfolders (unless `--recursive` is specified). It does not use the network.

## Portal document list (optional)

If a client-portal export (Excel or CSV) is in the drawings folder, TBCheck compares each PDF with that list. This is a read-only check; it does not update the portal or any register.

**How the list is chosen**

- Drop the spreadsheet onto `TBCheck.exe` (Windows passes that path as an argument). PDFs are still taken from the folder that contains the exe.
- Or leave the export in the drawings folder. Names containing Listing, Document List, Asite, 4Project, Export, or Dump are preferred. IRS / Drawing Schedule / TBCheck reports are ignored.
- Or pass `--document-list path\to\export.xlsx`, or `drawing-qa check path\to\export.xlsx` (PDFs are scanned in that file's folder).

If no usable list is found, the rest of the QA run is unchanged.

**What is checked**

- Drawing already on the portal: this issue must be **one revision up** (P01→P02, C01→C02). Moving from any P revision to **C01** is also allowed. Same revision, skipped numbers (P01→P03), or going backwards is flagged.
- Drawing not on the portal: first issue should be **P01**. **WCR** also allows **C01** (most of that project skips P and starts at C01).
- Titles are compared when both the portal list and the title block have one. Wording stays neutral: they should match, so one needs changing.

If the portal list has a workflow/status column, TBCheck also writes `{project}_{ddmmyy}_document_control.xlsx` for the client's document control, and a **Document control** tab in the main workbook. Drag the sidecar into an email. It only lists drawings that **cannot be uploaded** because the issue already on the portal is not status A, B, or C (so it cannot be superseded). Proposed revision is the next issue after the current portal revision — after any designer corrections — so a skipped drawing revision (C01 on the portal, C03 on the sheet) is shown as C02, not C03. The sheet shows a count of those files only, then document reference, title, current revision, proposed revision, and the current portal status with “Please change to A, B, or C”. Drawings that are not on the portal yet, or that are already A/B/C, are omitted. Project-specific status wordings (for example 4Projects “A Proceed”, Asite “A - Authorized and Accepted”, WCR “EA+DM - Status A”, Holloway Park “Construction”) are in `document_lists.yaml`.

Column headers are matched by name (not letter) using [`src/drawing_qa/default_config/document_lists.yaml`](src/drawing_qa/default_config/document_lists.yaml). That file covers 4Projects, Asite, and DocHosting CSV dumps. Per-project `first_revisions`, status maps, and filename search keys live in the same file.

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

Default layouts live in [`src/drawing_qa/default_config/title_blocks/`](src/drawing_qa/default_config/title_blocks/). Purpose-of-issue checking uses [`src/drawing_qa/default_config/suitability.yaml`](src/drawing_qa/default_config/suitability.yaml). Add a `projects:` list keyed by the ISO project code (first filename field, e.g. `R456` Trillium, `R459` Oval C+D, `J106309` Barking Riverside). Projects with no list use `suggested:` (Oval C+D) as the whitelist. P vs C pairing (`PURPOSE_MISMATCH`) is the `purpose:` block in that same file. A revision-history description is only compared with the current purpose when that row matches the whitelist; other history text is treated as a note. To customize a deployed copy, put YAML files in `config\title_blocks\` next to the exe and include `config\settings.yaml` plus `config\suitability.yaml`.

Typical workflow for a new style:

1. Run `drawing-qa inspect some.pdf` and look at the cropped PNGs plus dumped coordinates.
2. Copy an existing YAML file.
3. Adjust `region` (fractions of page width/height, origin at top-left).
4. Set `required_anchor_groups` to labels that uniquely identify the style (`DRAWING NO`, `REV`, …).
5. Map each field to the printed heading via `labels`. `direction: auto` tries to the right of the heading, then below it.

## Report

The workbook has six sheets, plus a separate one-tab designer workbook for email. Send **Designer actions** (or the `_designer.xlsx` file) to the design team. Use **Review needed** when you need the full evidence.

Reports are named `{project}_{ddmmyy}.xlsx` from the project name in `suitability.yaml` (or the ISO project code if there is no name) and today's date. A matching `{project}_{ddmmyy}_designer.xlsx` is written beside it. If a portal document list with a status column was used, `{project}_{ddmmyy}_document_control.xlsx` is written for the client.

- **Summary** — confidence counts, status counts, rename counts when files were renamed, and what each status means
- **Designer actions** — short counts at the top, then drawing number, title, and plain-language changes for CAD. Same drawings as Review needed; no previews. Purpose-of-issue issues point at the approved list at the bottom of that sheet rather than guessing a status. The `_designer.xlsx` file is this sheet on its own.
- **Document control** — also a `_document_control.xlsx` file for email. Drawings that cannot be uploaded until the portal status is A, B, or C. Proposed revision is the next portal issue after designer corrections (not a skipped or wrong revision on the drawing).
- **Review needed** — mismatches, history disagreements, incomplete reads, undetected layouts, parse errors, plus field previews
- **DWG pairing** — missing CAD copies and `.1` vs `-1` sheet-number differences
- **High confidence** — filename, current title block, and latest history revision/status agree (main date may be the first or latest history date)
- **All documents** — every PDF

Data rows include **File (as scanned)** (name at the start of the run), **New filename**, and **Rename result** so the workbook still makes sense after files have been renamed on disk.

Each data row is medium height and includes a **preview strip**: five tight crops (doc ref, title, revision, suitability, date) — not the whole title block.

| Status | Meaning |
| --- | --- |
| `MATCH` | Filename agrees with the current title block; latest history revision/status match current; date matches the first or latest history date |
| `MISMATCH` | Filename disagrees with the current title-block values; column A names the field (`MISMATCH: TITLE`) |
| `HISTORY_MISMATCH` | Current revision disagrees with the latest history row, the main date matches neither the first nor the latest history date, or the latest history row is a whitelist purpose that disagrees with the current purpose |
| `INCOMPLETE` | Layout found, but a required field was missing |
| `UNDETECTED` | No configured layout scored high enough |
| `FILENAME_PARSE_ERROR` | Filename is not ISO 19650; title-block values are still reported for manual review |
| `SPELLING_ERROR` | Possible spelling error in the title |
| `DATE_REGRESSION` | Later revision in history has an earlier date |
| `DUPLICATE_REFERENCE` | More than one PDF has the same document reference |
| `SUITABILITY_ERROR` | Purpose of issue is not on the project whitelist (or `suggested:` when the project has no list) |
| `PURPOSE_MISMATCH` | P revision with a construction purpose, or C revision with a review purpose (`purpose:` in `suitability.yaml`) |
| `DWG_ISSUE` | DWG missing, or paired DWG uses `-1` instead of `.1` (or the reverse) |
| `PORTAL_REVISION` | Revision is not the next issue after the portal document list (or not a valid first issue if the drawing is new) |
| `PORTAL_TITLE` | Title disagrees with the portal document list |
| `ERROR` | PDF could not be read |
| `MULTIPLE_ISSUES` | More than one issue; column A lists them all |

Document reference and revision are **required** when the filename is ISO 19650. Title, suitability, and date are compared when both sides have a value. History revision and suitability are checked against the latest row. The main title-block date may be either the original issue date or the latest revision date (designers differ on this), so it is only flagged when it matches neither. History dates must still be sequential within the P series and within the C series.

## Tests and Linux freeze check

```bash
pytest
pip install -e ".[build]"
python scripts/build_exe.py
```

On Linux that produces `dist/TBCheck` and `dist/TBCheckRename` (not Windows `.exe` files). Build the Windows exes with `build_exe.bat` on Windows.
