from __future__ import annotations

from pathlib import Path

import pymupdf

A3_LANDSCAPE = (1190.55, 841.89)


def _page() -> tuple[pymupdf.Document, pymupdf.Page]:
    doc = pymupdf.open()
    page = doc.new_page(width=A3_LANDSCAPE[0], height=A3_LANDSCAPE[1])
    page.insert_text((40, 40), "GENERAL ARRANGEMENT", fontsize=18)
    return doc, page


def _draw_history(page, rows: list[tuple[str, str, str]], origin=(430, 610)) -> None:
    x, y = origin
    page.insert_text((x, y), "REV", fontsize=7)
    page.insert_text((x + 50, y), "DATE", fontsize=7)
    page.insert_text((x + 130, y), "DESCRIPTION", fontsize=7)
    for i, (rev, date, desc) in enumerate(rows):
        yy = y + 18 + i * 16
        page.insert_text((x, yy), rev, fontsize=8)
        page.insert_text((x + 50, yy), date, fontsize=8)
        page.insert_text((x + 130, yy), desc, fontsize=8)


def write_bottom_right_pdf(
    path: Path,
    *,
    document_reference: str,
    title: str,
    revision: str,
    suitability: str | None = None,
    date: str | None = None,
    history: list[tuple[str, str, str]] | None = None,
) -> Path:
    doc, page = _page()
    page.draw_rect(pymupdf.Rect(750, 600, 1175, 820), color=(0, 0, 0), width=1)
    page.insert_text((760, 630), "DRAWING TITLE", fontsize=8)
    page.insert_text((760, 655), title, fontsize=12)
    page.insert_text((760, 700), "DRAWING NO", fontsize=8)
    page.insert_text((860, 700), document_reference, fontsize=11)
    page.insert_text((1060, 690), "REV", fontsize=8)
    page.insert_text((1060, 712), revision, fontsize=12)
    if date:
        page.insert_text((760, 750), "DATE", fontsize=8)
        page.insert_text((820, 750), date, fontsize=11)
    if suitability:
        page.insert_text((960, 750), "STATUS", fontsize=8)
        page.insert_text((1020, 750), suitability, fontsize=10)
    if history:
        _draw_history(page, history)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def write_bottom_strip_pdf(
    path: Path,
    *,
    document_reference: str,
    title: str,
    revision: str,
    suitability: str | None = None,
    date: str | None = None,
) -> Path:
    doc, page = _page()
    page.draw_rect(pymupdf.Rect(30, 700, 1160, 825), color=(0, 0, 0), width=1)
    page.insert_text((50, 730), "DOCUMENT NUMBER", fontsize=8)
    page.insert_text((200, 730), document_reference, fontsize=11)
    page.insert_text((900, 730), "REVISION", fontsize=8)
    page.insert_text((1000, 730), revision, fontsize=12)
    page.insert_text((50, 790), "TITLE", fontsize=8)
    page.insert_text((120, 790), title, fontsize=11)
    if date:
        page.insert_text((520, 730), "DATE", fontsize=8)
        page.insert_text((570, 730), date, fontsize=11)
    if suitability:
        page.insert_text((700, 730), "STATUS", fontsize=8)
        page.insert_text((760, 730), suitability, fontsize=10)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def write_plain_pdf(path: Path, text: str = "No title block here") -> Path:
    doc, page = _page()
    page.insert_text((80, 200), text, fontsize=14)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path
