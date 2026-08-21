from __future__ import annotations

from io import BytesIO
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from drawing_qa.models import CheckStatus, Confidence, DocumentResult
from drawing_qa.preview import preview_size
from drawing_qa.timing import span as timing_span

STATUS_FILL = {
    CheckStatus.MATCH: PatternFill("solid", fgColor="C6EFCE"),
    CheckStatus.MISMATCH: PatternFill("solid", fgColor="FFC7CE"),
    CheckStatus.HISTORY_MISMATCH: PatternFill("solid", fgColor="F8CBAD"),
    CheckStatus.INCOMPLETE: PatternFill("solid", fgColor="FFEB9C"),
    CheckStatus.UNDETECTED: PatternFill("solid", fgColor="DDEBF7"),
    CheckStatus.SPELLING_ERROR: PatternFill("solid", fgColor="E4DFEC"),
    CheckStatus.DUPLICATE_REFERENCE: PatternFill("solid", fgColor="FFB6C1"),
    CheckStatus.DATE_REGRESSION: PatternFill("solid", fgColor="FFA07A"),
    CheckStatus.SUITABILITY_ERROR: PatternFill("solid", fgColor="F4B183"),
    CheckStatus.FILENAME_PARSE_ERROR: PatternFill("solid", fgColor="F4B183"),
    CheckStatus.ERROR: PatternFill("solid", fgColor="D9D9D9"),
    CheckStatus.MULTIPLE_ISSUES: PatternFill("solid", fgColor="C65911"),
}
CONF_FILL = {
    Confidence.HIGH: PatternFill("solid", fgColor="C6EFCE"),
    Confidence.REVIEW: PatternFill("solid", fgColor="FFEB9C"),
}
BODY_FONT = Font(size=10)
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
HEADER_ALIGN = Alignment(wrap_text=True, vertical="center", horizontal="center")
WRAP = Alignment(wrap_text=True, vertical="center")
PREVIEW_W, PREVIEW_H = preview_size()
ROW_HEIGHT = 62
PREVIEW_COL_WIDTH = round(PREVIEW_W / 7.0, 1)

COLUMNS = [
    ("Status", 42),
    ("Confidence", 12),
    ("File (as scanned)", 35),
    ("Filename doc ref", 35),
    ("Title-block doc ref", 35),
    ("Filename title", 35),
    ("Title", 35),
    ("Rev (file)", 11),
    ("Rev (drawing)", 13),
    ("Status / suitability", 25),
    ("Date", 12),
    ("History latest", 40),
    ("History check", 14),
    ("Preview (detected fields)", PREVIEW_COL_WIDTH),
    ("New filename", 45),
    ("Rename result", 28),
    ("DWG pairing", 35),
    ("Notes", 60),
]
PREVIEW_COL = 14
HISTORY_CHECK_COL = 13
RENAME_RESULT_COL = 16

RENAME_FILL = {
    "Renamed": PatternFill("solid", fgColor="BDD7EE"),
    "Unchanged": PatternFill("solid", fgColor="C6EFCE"),
    "Not renamed": PatternFill("solid", fgColor="D9D9D9"),
    "Failed": PatternFill("solid", fgColor="FFC7CE"),
}


def _comp(result: DocumentResult, name: str):
    for item in result.comparisons:
        if item.name == name:
            return item
    return None


def _hcomp(result: DocumentResult, name: str):
    for item in result.history_comparisons:
        if item.name == name:
            return item
    return None


def _dwg_pairing_text(result: DocumentResult) -> str:
    """Generate text for DWG pairing column."""
    if result.paired_dwg:
        if result.dwg_mismatch:
            return f"{result.paired_dwg.name} (name mismatch)"
        return result.paired_dwg.name
    if result.dwg_files_present:
        return "No matching DWG"
    return "No DWGs in folder"


def _history_check(result: DocumentResult) -> str:
    if not result.titleblock.history.latest:
        return "No history"
    mismatches = [item for item in result.history_comparisons if item.matched is False]
    if mismatches:
        return "Mismatch"
    if any(item.detail.startswith("current field taken") for item in result.history_comparisons):
        return "From history"
    return "Matches current"


def _latest_history_label(result: DocumentResult) -> str:
    latest = result.titleblock.history.latest
    if not latest:
        return ""
    parts = [p for p in (latest.revision, latest.date, latest.suitability) if p]
    return " · ".join(parts)


def _rename_fill(result: DocumentResult) -> PatternFill | None:
    text = result.rename_result or ""
    if text.startswith("Renamed"):
        return RENAME_FILL["Renamed"]
    if text.startswith("Unchanged"):
        return RENAME_FILL["Unchanged"]
    if text.startswith("Failed"):
        return RENAME_FILL["Failed"]
    if text.startswith("Not renamed"):
        return RENAME_FILL["Not renamed"]
    return None


def _row(result: DocumentResult) -> list[object]:
    return [
        result.status_label(),
        result.confidence.value,
        result.original_filename or result.path.name,
        result.filename.document_reference or "",
        result.titleblock.document_reference or "",
        result.filename.title or "",
        result.titleblock.title or "",
        result.filename.revision or "",
        result.titleblock.revision or "",
        result.titleblock.suitability or "",
        result.titleblock.date or "",
        _latest_history_label(result),
        _history_check(result),
        "",  # Preview column (filled separately)
        result.suggested_filename or "",
        result.rename_result or "",
        _dwg_pairing_text(result),
        "; ".join(result.notes + ([result.error] if result.error else [])),
    ]


def _style_header(ws: Worksheet) -> None:
    for col, (_name, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}1"
    ws.sheet_view.showGridLines = False


def _add_preview(ws: Worksheet, row_idx: int, png: bytes, keep: list) -> None:
    buffer = BytesIO(png)
    buffer.name = "preview.png"
    image = XLImage(buffer)
    image.width = PREVIEW_W
    image.height = PREVIEW_H
    image.anchor = f"{get_column_letter(PREVIEW_COL)}{row_idx}"
    ws.add_image(image)
    keep.append(image)


def _write_rows(ws: Worksheet, results: list[DocumentResult], keep: list) -> None:
    ws.append([name for name, _width in COLUMNS])
    _style_header(ws)
    if not results:
        ws.append(["(none)"] + [""] * (len(COLUMNS) - 1))
        return
    for result in results:
        ws.append(_row(result))
        row_idx = ws.max_row
        ws.row_dimensions[row_idx].height = ROW_HEIGHT
        status_fill = STATUS_FILL.get(result.status)
        if result.status == CheckStatus.MULTIPLE_ISSUES:
            status_fill = STATUS_FILL[CheckStatus.MULTIPLE_ISSUES]
        if status_fill:
            ws.cell(row_idx, 1).fill = status_fill
        conf_fill = CONF_FILL.get(result.confidence)
        if conf_fill:
            ws.cell(row_idx, 2).fill = conf_fill
        history_fill = None
        check = _history_check(result)
        if check == "Mismatch":
            history_fill = STATUS_FILL[CheckStatus.HISTORY_MISMATCH]
        elif check == "Matches current":
            history_fill = STATUS_FILL[CheckStatus.MATCH]
        if history_fill:
            ws.cell(row_idx, HISTORY_CHECK_COL).fill = history_fill
        for col in range(1, len(COLUMNS) + 1):
            cell = ws.cell(row_idx, col)
            cell.alignment = WRAP
            cell.font = BODY_FONT
        if result.preview_png:
            with timing_span("report_embed_previews"):
                _add_preview(ws, row_idx, result.preview_png, keep)
        rename_fill = _rename_fill(result)
        if rename_fill:
            ws.cell(row_idx, RENAME_RESULT_COL).fill = rename_fill
    last = get_column_letter(len(COLUMNS))
    ws.auto_filter.ref = f"A1:{last}{ws.max_row}"


def _write_summary(ws: Worksheet, results: list[DocumentResult]) -> None:
    counts = Counter(item.status for item in results)
    conf_counts = Counter(item.confidence for item in results)
    ws["A1"] = "Drawing title-block QA"
    ws["A1"].font = Font(bold=True, size=10, color="1F4E79")
    ws["A2"] = "Generated"
    ws["B2"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ws["A3"] = "Documents checked"
    ws["B3"] = len(results)
    ws["A4"] = "Start here"
    ws["B4"] = "Open the Review needed tab first. High confidence can be sampled more lightly."
    ws["B4"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("B4:F4")
    for coord in ("A2", "B2", "A3", "B3", "A4", "B4"):
        ws[coord].font = BODY_FONT

    ws["A6"] = "Confidence"
    ws["B6"] = "Count"
    ws["A6"].font = HEADER_FONT
    ws["A6"].fill = HEADER_FILL
    ws["B6"].font = HEADER_FONT
    ws["B6"].fill = HEADER_FILL
    ws["A7"] = Confidence.REVIEW.value
    ws["B7"] = conf_counts.get(Confidence.REVIEW, 0)
    ws["A7"].fill = CONF_FILL[Confidence.REVIEW]
    ws["A7"].font = BODY_FONT
    ws["B7"].font = BODY_FONT
    ws["A8"] = Confidence.HIGH.value
    ws["B8"] = conf_counts.get(Confidence.HIGH, 0)
    ws["A8"].fill = CONF_FILL[Confidence.HIGH]
    ws["A8"].font = BODY_FONT
    ws["B8"].font = BODY_FONT

    ws["A10"] = "Status"
    ws["B10"] = "Count"
    ws["C10"] = "Meaning"
    for col in ("A", "B", "C"):
        ws[f"{col}10"].font = HEADER_FONT
        ws[f"{col}10"].fill = HEADER_FILL
    meanings = {
        CheckStatus.MATCH: "Filename and current title-block values agree; history latest matches current",
        CheckStatus.MISMATCH: "Filename disagrees with the current title-block values (column A names the field)",
        CheckStatus.HISTORY_MISMATCH: "Current title block disagrees with the latest revision-history row",
        CheckStatus.INCOMPLETE: "Layout found, but the document reference could not be read from the title block",
        CheckStatus.UNDETECTED: "No configured layout scored high enough",
        CheckStatus.SPELLING_ERROR: "Possible spelling error detected in title",
        CheckStatus.DUPLICATE_REFERENCE: "Multiple PDFs have the same document reference",
        CheckStatus.DATE_REGRESSION: "Revision dates go backwards (later rev has earlier date)",
        CheckStatus.SUITABILITY_ERROR: "Purpose of issue / suitability is not in the whitelist",
        CheckStatus.FILENAME_PARSE_ERROR: "Filename is not ISO 19650; title-block values are still shown",
        CheckStatus.ERROR: "PDF could not be read",
        CheckStatus.MULTIPLE_ISSUES: "More than one issue — see Notes and the status list in column A",
    }
    row = 11
    for status in CheckStatus:
        ws.cell(row, 1, status.value)
        ws.cell(row, 2, counts.get(status, 0))
        ws.cell(row, 3, meanings[status])
        fill = STATUS_FILL.get(status)
        if fill:
            ws.cell(row, 1).fill = fill
        ws.cell(row, 3).alignment = Alignment(wrap_text=True)
        for col in range(1, 4):
            ws.cell(row, col).font = BODY_FONT
        row += 1

    if any(item.rename_result for item in results):
        row += 1
        ws.cell(row, 1, "Rename")
        ws.cell(row, 2, "Count")
        ws.cell(row, 3, "Meaning")
        for col in ("A", "B", "C"):
            ws[f"{col}{row}"].font = HEADER_FONT
            ws[f"{col}{row}"].fill = HEADER_FILL
        row += 1
        renamed = sum(1 for item in results if (item.rename_result or "").startswith("Renamed"))
        unchanged = sum(1 for item in results if (item.rename_result or "").startswith("Unchanged"))
        skipped = sum(1 for item in results if (item.rename_result or "").startswith("Not renamed"))
        failed = sum(1 for item in results if (item.rename_result or "").startswith("Failed"))
        for label, count, fill in (
            ("Renamed", renamed, RENAME_FILL["Renamed"]),
            ("Unchanged", unchanged, RENAME_FILL["Unchanged"]),
            ("Not renamed / skipped", skipped, RENAME_FILL["Not renamed"]),
            ("Failed", failed, RENAME_FILL["Failed"]),
        ):
            ws.cell(row, 1, label)
            ws.cell(row, 2, count)
            ws.cell(row, 1).fill = fill
            for col in range(1, 3):
                ws.cell(row, col).font = BODY_FONT
            row += 1
        ws.cell(row, 1, "File (as scanned) is the name at the start of this run.")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        ws.cell(row, 1).font = BODY_FONT
        ws.cell(row, 1).alignment = Alignment(wrap_text=True)
        row += 1
        ws.cell(row, 1, "New filename is the name after this run (or the intended name if the rename was not applied).")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
        ws.cell(row, 1).font = BODY_FONT
        ws.cell(row, 1).alignment = Alignment(wrap_text=True)

    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 80
    ws.row_dimensions[4].height = 32


def write_report(results: list[DocumentResult], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    keep: list = []
    wb._preview_images = keep  # prevent GC of BytesIO-backed images

    with timing_span("report_build"):
        summary = wb.active
        summary.title = "Summary"
        _write_summary(summary, results)

        review = [
            item for item in results if item.confidence == Confidence.REVIEW
        ]
        high = [item for item in results if item.confidence == Confidence.HIGH]

        review_sheet = wb.create_sheet("Review needed")
        _write_rows(review_sheet, review, keep)
        high_sheet = wb.create_sheet("High confidence")
        _write_rows(high_sheet, high, keep)
        all_sheet = wb.create_sheet("All documents")
        _write_rows(all_sheet, results, keep)

    with timing_span("report_save"):
        wb.save(output)
    return output
