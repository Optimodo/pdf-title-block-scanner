from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from drawing_qa.models import CheckStatus, DocumentResult

STATUS_FILL = {
    CheckStatus.MATCH: PatternFill("solid", fgColor="C6EFCE"),
    CheckStatus.MISMATCH: PatternFill("solid", fgColor="FFC7CE"),
    CheckStatus.INCOMPLETE: PatternFill("solid", fgColor="FFEB9C"),
    CheckStatus.UNDETECTED: PatternFill("solid", fgColor="DDEBF7"),
    CheckStatus.FILENAME_PARSE_ERROR: PatternFill("solid", fgColor="F4B183"),
    CheckStatus.ERROR: PatternFill("solid", fgColor="D9D9D9"),
}

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


COLUMNS = [
    ("Status", 16),
    ("File", 45),
    ("Detected layout", 22),
    ("Layout score", 14),
    ("Filename document reference", 36),
    ("Title-block document reference", 36),
    ("Document reference match", 16),
    ("Filename revision", 18),
    ("Title-block revision", 18),
    ("Revision match", 14),
    ("Filename title", 36),
    ("Title-block title", 36),
    ("Title match", 12),
    ("Notes", 50),
]


def _comp(result: DocumentResult, name: str):
    for item in result.comparisons:
        if item.name == name:
            return item
    return None


def _match_label(value: bool | None) -> str:
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "n/a"


def _row(result: DocumentResult) -> list[object]:
    doc = _comp(result, "document_reference")
    rev = _comp(result, "revision")
    title = _comp(result, "title")
    return [
        result.status.value,
        result.path.name,
        result.titleblock.layout_name or "",
        result.titleblock.score,
        result.filename.document_reference or "",
        result.titleblock.document_reference or "",
        _match_label(doc.matched if doc else None),
        result.filename.revision or "",
        result.titleblock.revision or "",
        _match_label(rev.matched if rev else None),
        result.filename.title or "",
        result.titleblock.title or "",
        _match_label(title.matched if title else None),
        "; ".join(result.notes + ([result.error] if result.error else [])),
    ]


def _style_header(ws) -> None:
    for col, (_name, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"


def _write_rows(ws, results: list[DocumentResult]) -> None:
    ws.append([name for name, _width in COLUMNS])
    _style_header(ws)
    for result in results:
        ws.append(_row(result))
        fill = STATUS_FILL.get(result.status)
        row_idx = ws.max_row
        if fill:
            ws.cell(row_idx, 1).fill = fill
        for col in range(1, len(COLUMNS) + 1):
            ws.cell(row_idx, col).alignment = WRAP
    ws.row_dimensions[1].height = 22


def write_report(results: list[DocumentResult], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    summary = wb.active
    summary.title = "Summary"
    counts = Counter(item.status for item in results)
    summary.append(["Drawing title-block QA"])
    summary["A1"].font = Font(bold=True, size=14)
    summary.append(["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    summary.append(["Documents checked", len(results)])
    summary.append([])
    summary.append(["Status", "Count"])
    summary["A5"].font = HEADER_FONT
    summary["A5"].fill = HEADER_FILL
    summary["B5"].font = HEADER_FONT
    summary["B5"].fill = HEADER_FILL
    for status in CheckStatus:
        summary.append([status.value, counts.get(status, 0)])
        cell = summary.cell(summary.max_row, 1)
        fill = STATUS_FILL.get(status)
        if fill:
            cell.fill = fill
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 14

    all_sheet = wb.create_sheet("All documents")
    _write_rows(all_sheet, results)

    mismatches = [
        item
        for item in results
        if item.status in {CheckStatus.MISMATCH, CheckStatus.INCOMPLETE, CheckStatus.UNDETECTED, CheckStatus.FILENAME_PARSE_ERROR, CheckStatus.ERROR}
    ]
    mismatch_sheet = wb.create_sheet("Needs attention")
    _write_rows(mismatch_sheet, mismatches)

    matches = [item for item in results if item.status == CheckStatus.MATCH]
    match_sheet = wb.create_sheet("Matches")
    _write_rows(match_sheet, matches)

    wb.save(output)
    return output
