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
    client: str | None = None,
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
    if client:
        page.insert_text((760, 780), "CLIENT", fontsize=8)
        page.insert_text((820, 780), client, fontsize=11)
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
    client: str | None = None,
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
    if client:
        page.insert_text((50, 810), "CLIENT", fontsize=8)
        page.insert_text((120, 810), client, fontsize=11)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def write_mbs_classic_pdf(
    path: Path,
    *,
    document_reference: str,
    title: str,
    revision: str,
    suitability: str = "S3 - Review and Comment",
    date: str = "27/08/26",
    client: str = "Berkeley Homes",
    history: list[tuple[str, str, str]] | None = None,
) -> Path:
    """Older MBS right-hand block: values sit in page clips; headings are not text."""
    width, height = 3370.0, 2384.0
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)

    def put(xf: float, yf: float, text: str, size: float = 12) -> None:
        page.insert_text((xf * width, yf * height), text, fontsize=size)

    rows = history or [
        (revision, date, suitability),
        ("P01", "04/08/26", "S3 - Review and comment"),
    ]
    y = 0.705
    for rev, when, desc in rows:
        put(0.859, y, rev, 9)
        put(0.871, y, when, 9)
        put(0.891, y, desc, 9)
        y += 0.007
    put(0.859, 0.725, "Rev", 8)
    put(0.872, 0.725, "Date", 8)
    put(0.892, 0.725, "Revision", 8)
    put(0.906, 0.725, "Notes", 8)
    put(0.980, 0.725, "By", 8)
    lines = title.split("\n")
    put(0.874, 0.830, lines[0], 12)
    if len(lines) > 1:
        put(0.907, 0.839, lines[1], 12)
    put(0.860, 0.860, suitability, 11)
    put(0.863, 0.898, document_reference, 14)
    put(0.976, 0.898, revision, 16)
    if client:
        put(0.874, 0.790, client, 10)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def write_mbs_bottom_pdf(
    path: Path,
    *,
    document_reference: str,
    title: str,
    revision: str,
    suitability: str = "S5 - Construction",
    date: str = "20.04.2026",
    client: str = "Berkeley Homes",
    history: list[tuple[str, str, str]] | None = None,
) -> Path:
    """Portrait MBS bottom title block (Status, Number, Amendments)."""
    width, height = 2384.0, 3370.0
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)

    def put(xf: float, yf: float, text: str, size: float = 12) -> None:
        page.insert_text((xf * width, yf * height), text, fontsize=size)

    put(0.816, 0.894, "Project", 8)
    put(0.853, 0.900, "Oval Village - Block C", 12)
    put(0.816, 0.910, "Title", 8)
    put(0.862, 0.925, title, 12)
    put(0.647, 0.920, "Status", 8)
    put(0.691, 0.928, suitability, 14)
    put(0.704, 0.944, "Date", 8)
    put(0.730, 0.945, date, 10)
    put(0.816, 0.941, "Client", 8)
    put(0.877, 0.948, client, 10)
    rows = history or [
        (revision, "27.08.26", "S3 - Added landing valve"),
        ("P01", "20.04.26", "S3 - Review and Comment"),
    ]
    y = 0.957
    for rev, when, desc in rows:
        put(0.479, y, rev, 9)
        put(0.492, y, when, 9)
        put(0.510, y, desc, 9)
        put(0.635, y, "JG", 9)
        y += 0.006
    put(0.479, 0.971, "Rev", 8)
    put(0.494, 0.971, "Date", 8)
    put(0.557, 0.971, "Description", 8)
    put(0.636, 0.971, "By", 8)
    put(0.786, 0.963, "Revision", 8)
    put(0.785, 0.973, revision, 16)
    put(0.648, 0.963, "Number", 8)
    put(0.660, 0.975, document_reference, 12)
    put(0.547, 0.980, "Amendments", 9)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def write_mbs_right_pdf(
    path: Path,
    *,
    document_reference: str,
    title: str,
    revision: str,
    suitability: str = "S3",
    date: str = "14.08.26",
    client: str = "Berkeley",
    history: list[tuple[str, str, str]] | None = None,
) -> Path:
    """Landscape sheet with an MBS-style right-hand title block (visual coords)."""
    doc = pymupdf.open()
    page = doc.new_page(width=2384, height=1684)
    page.insert_text((40, 40), "SPRINKLER LAYOUT", fontsize=18)
    # Amendments table (newest row above the column headers)
    rows = history or [(revision, date, f"{suitability} - Review & Comment")]
    y = 1058
    for rev, when, desc in rows:
        page.insert_text((1916, y), rev, fontsize=9)
        page.insert_text((1945, y), when, fontsize=9)
        page.insert_text((1990, y), desc, fontsize=9)
        y += 16
    page.insert_text((1915, 1088), "Rev", fontsize=8)
    page.insert_text((1952, 1088), "Date", fontsize=8)
    page.insert_text((2102, 1088), "Description", fontsize=8)
    page.insert_text((2288, 1088), "By", fontsize=8)
    page.insert_text((2077, 1118), "Amendments", fontsize=9)
    page.insert_text((1918, 1140), "Project", fontsize=8)
    page.insert_text((2011, 1170), "Oval Village Block D", fontsize=12)
    page.insert_text((1918, 1196), "Title", fontsize=8)
    title_y = 1240
    for line in title.split("\n"):
        page.insert_text((1923, title_y), line, fontsize=12)
        title_y += 28
    page.insert_text((1918, 1296), "Client", fontsize=8)
    page.insert_text((2085, 1320), client, fontsize=10)
    page.insert_text((1914, 1446), "Suitability", fontsize=8)
    page.insert_text((2041, 1468), "REVIEW & COMMENT", fontsize=11)
    page.insert_text((2271, 1468), suitability, fontsize=12)
    page.insert_text((2051, 1528), "Date", fontsize=8)
    page.insert_text((2126, 1534), date, fontsize=10)
    page.insert_text((1918, 1592), "Number", fontsize=8)
    page.insert_text((1946, 1640), document_reference, fontsize=14)
    page.insert_text((2247, 1592), "Revision", fontsize=8)
    page.insert_text((2246, 1640), revision, fontsize=18)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def write_rotated_number_pdf(path: Path) -> Path:
    """Portrait page rotated 270° with a label in unrotated space (bottom-left)."""
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=400)
    page.insert_text((20, 380), "Number", fontsize=11)
    page.set_rotation(270)
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
