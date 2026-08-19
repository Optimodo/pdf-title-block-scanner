from pathlib import Path

import pymupdf

from drawing_qa.extract import extract_near_label_words, extract_words, take_until_label
from drawing_qa.models import Word
from tests.pdf_fixtures import write_rotated_number_pdf


def _words(*texts: str) -> list[Word]:
    result = []
    x = 0.0
    for text in texts:
        result.append(Word(x0=x, y0=0, x1=x + 10, y1=8, text=text))
        x += 12
    return result


def test_take_until_label_stops_at_next_heading():
    words = _words("ABC-WXY-ZZ-00-DR-A-0001", "REV", "P01")
    kept = take_until_label(words, ["REV", "REVISION"])
    assert [w.text for w in kept] == ["ABC-WXY-ZZ-00-DR-A-0001"]


def test_extract_words_maps_rotated_page_to_visual_space(tmp_path: Path):
    pdf = write_rotated_number_pdf(tmp_path / "rotated.pdf")
    doc = pymupdf.open(pdf)
    page = doc[0]
    assert page.rotation == 270
    width, height = page.rect.width, page.rect.height
    words = extract_words(page)
    doc.close()
    number = next(word for word in words if word.text == "Number")
    assert number.x0 > width * 0.7
    assert number.y0 > height * 0.7


def test_take_until_label_keeps_all_when_no_heading():
    words = _words("Ground", "Floor", "GA")
    kept = take_until_label(words, ["REV"])
    assert [w.text for w in kept] == ["Ground", "Floor", "GA"]


def test_date_value_slightly_below_label_is_captured():
    words = [
        Word(x0=2180, y0=1593, x1=2195, y1=1602, text="Date"),
        Word(x0=2204, y0=1596, x1=2260, y1=1615, text="01.06.2026"),
        Word(x0=2271, y0=1593, x1=2289, y1=1604, text="Scale"),
        Word(x0=2291, y0=1593, x1=2310, y1=1604, text="@A1"),
    ]
    found = extract_near_label_words(words, ["DATE"], "auto", stop_labels=["SCALE"])
    assert found is not None
    assert found[0] == "01.06.2026"


def test_suitability_code_and_description_stop_at_designed_by():
    words = [
        Word(x0=2089, y0=1520, x1=2120, y1=1529, text="Suitability"),
        Word(x0=2171, y0=1529, x1=2268, y1=1546, text="CONSTRUCTION"),
        Word(x0=2341, y0=1525, x1=2353, y1=1549, text="A"),
        Word(x0=2089, y0=1557, x1=2119, y1=1567, text="Designed"),
        Word(x0=2121, y0=1557, x1=2135, y1=1567, text="by"),
    ]
    found = extract_near_label_words(words, ["SUITABILITY"], "auto", stop_labels=["DESIGNED BY"])
    assert found is not None
    from drawing_qa.tokens import extract_suitability

    assert extract_suitability(found[0]) == "A - CONSTRUCTION"
