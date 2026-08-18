from __future__ import annotations

from pathlib import Path

import pymupdf

A3_LANDSCAPE = (1190.55, 841.89)


def _page() -> tuple[pymupdf.Document, pymupdf.Page]:
    doc = pymupdf.open()
    page = doc.new_page(width=A3_LANDSCAPE[0], height=A3_LANDSCAPE[1])
    page.insert_text((40, 40), "GENERAL ARRANGEMENT", fontsize=18)
    return doc, page


def write_bottom_right_pdf(
    path: Path,
    *,
    document_reference: str,
    title: str,
    revision: str,
) -> Path:
    doc, page = _page()
    # Title-block outline in the bottom-right region used by bottom_right.yaml
    page.draw_rect(pymupdf.Rect(750, 600, 1175, 820), color=(0, 0, 0), width=1)
    page.insert_text((760, 630), "DRAWING TITLE", fontsize=8)
    page.insert_text((760, 655), title, fontsize=12)
    page.insert_text((760, 760), "DRAWING NO", fontsize=8)
    page.insert_text((860, 760), document_reference, fontsize=11)
    page.insert_text((1060, 740), "REV", fontsize=8)
    page.insert_text((1060, 765), revision, fontsize=12)
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
) -> Path:
    doc, page = _page()
    page.draw_rect(pymupdf.Rect(30, 700, 1160, 825), color=(0, 0, 0), width=1)
    page.insert_text((50, 730), "DOCUMENT NUMBER", fontsize=8)
    page.insert_text((200, 730), document_reference, fontsize=11)
    page.insert_text((900, 730), "REVISION", fontsize=8)
    page.insert_text((1000, 730), revision, fontsize=12)
    page.insert_text((50, 790), "TITLE", fontsize=8)
    page.insert_text((120, 790), title, fontsize=11)
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
