from pathlib import Path

import pymupdf

from drawing_qa.extract import (
    clear_page_word_cache,
    extract_near_label_words,
    extract_words,
    take_until_label,
)
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
    clear_page_word_cache()
    number = next(word for word in words if word.text == "Number")
    assert number.x0 > width * 0.7
    assert number.y0 > height * 0.7


def test_extract_words_caches_full_page_get_text(tmp_path: Path, monkeypatch):
    pdf = write_rotated_number_pdf(tmp_path / "cache.pdf")
    doc = pymupdf.open(pdf)
    page = doc[0]
    clear_page_word_cache()
    calls = {"n": 0}
    original = page.get_text

    def counting_get_text(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(page, "get_text", counting_get_text)
    first = extract_words(page)
    second = extract_words(page)
    assert calls["n"] == 1
    assert [w.text for w in first] == [w.text for w in second]
    clear_page_word_cache(page)
    extract_words(page)
    assert calls["n"] == 2
    doc.close()
    clear_page_word_cache()


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
    found = extract_near_label_words(
        words, ["SUITABILITY"], "auto", stop_labels=["DESIGNED BY"]
    )
    assert found is not None
    from drawing_qa.tokens import extract_suitability

    assert extract_suitability(found[0]) == "A - CONSTRUCTION"


def test_drawing_number_below_and_left_of_label():
    words = [
        Word(x0=3140, y0=2308, x1=3183, y1=2320, text="Drawing"),
        Word(x0=3185, y0=2308, x1=3200, y1=2320, text="No"),
        Word(x0=3271, y0=2308, x1=3310, y1=2320, text="Revision"),
        Word(x0=3064, y0=2323, x1=3280, y1=2336, text="R456-MAL20-BI-02-DR-W-655-004"),
        Word(x0=3276, y0=2320, x1=3300, y1=2336, text="P01"),
    ]
    found = extract_near_label_words(
        words, ["DRAWING NO"], "auto", stop_labels=["REVISION", "REV"]
    )
    assert found is not None
    assert "R456-MAL20-BI-02-DR-W-655-004" in found[0]


def test_title_includes_word_starting_under_the_label():
    words = [
        Word(x0=3060, y0=2189, x1=3091, y1=2201, text="Drawing"),
        Word(x0=3093, y0=2189, x1=3110, y1=2201, text="Title"),
        Word(x0=3064, y0=2208, x1=3092, y1=2220, text="Block"),
        Word(x0=3094, y0=2208, x1=3100, y1=2220, text="I"),
        Word(x0=3106, y0=2208, x1=3159, y1=2220, text="SVP&RWP"),
        Word(x0=3251, y0=2208, x1=3280, y1=2220, text="Level"),
        Word(x0=3280, y0=2208, x1=3310, y1=2220, text="03-13"),
        Word(x0=3060, y0=2274, x1=3084, y1=2286, text="Scale"),
    ]
    found = extract_near_label_words(
        words, ["DRAWING TITLE", "TITLE"], "auto", stop_labels=["SCALE"]
    )
    assert found is not None
    assert found[0].startswith("Block I")
    assert "03-13" in found[0]


def test_wrapped_title_keeps_second_line_with_auto_direction():
    """Right-of-label capture must not drop a continuation line below."""
    words = [
        Word(x0=3060, y0=2189, x1=3091, y1=2201, text="Drawing"),
        Word(x0=3093, y0=2189, x1=3110, y1=2201, text="Title"),
        Word(x0=3073, y0=2202, x1=3110, y1=2214, text="BLOCK"),
        Word(x0=3111, y0=2202, x1=3120, y1=2214, text="D"),
        Word(x0=3121, y0=2202, x1=3185, y1=2214, text="APARTMENT"),
        Word(x0=3186, y0=2202, x1=3214, y1=2214, text="TYPE"),
        Word(x0=3215, y0=2202, x1=3230, y1=2214, text="A1"),
        Word(x0=3231, y0=2202, x1=3310, y1=2214, text="VENTILATION"),
        Word(x0=3163, y0=2214, x1=3210, y1=2226, text="LAYOUT"),
        Word(x0=3060, y0=2274, x1=3084, y1=2286, text="Scale"),
    ]
    found = extract_near_label_words(
        words, ["DRAWING TITLE", "TITLE"], "auto", stop_labels=["SCALE"]
    )
    assert found is not None
    assert found[0] == "BLOCK D APARTMENT TYPE A1 VENTILATION LAYOUT"


def test_title_ignores_drawing_notes_left_of_title_heading():
    """Sheet notes left of TITLE (grid '2-04', sizes) must not join the title."""
    words = [
        Word(x0=3048, y0=1903, x1=3061, y1=1912, text="Title"),
        Word(x0=2879, y0=1932, x1=2908, y1=1954, text="2-04"),
        Word(x0=2964, y0=1973, x1=2976, y1=1985, text="700"),
        Word(x0=3076, y0=1931, x1=3098, y1=1959, text="B2"),
        Word(x0=3103, y0=1931, x1=3109, y1=1959, text="-"),
        Word(x0=3114, y0=1931, x1=3196, y1=1959, text="Combined"),
        Word(x0=3201, y0=1931, x1=3292, y1=1959, text="Mechanical"),
        Word(x0=3058, y0=1954, x1=3112, y1=1981, text="Layout"),
        Word(x0=3117, y0=1954, x1=3123, y1=1981, text="-"),
        Word(x0=3128, y0=1954, x1=3211, y1=1981, text="Apartment"),
        Word(x0=3216, y0=1954, x1=3256, y1=1981, text="Type"),
        Word(x0=3261, y0=1954, x1=3311, y1=1981, text="B2-2B"),
        Word(x0=2906, y0=2030, x1=2923, y1=2042, text="1130"),
    ]
    found = extract_near_label_words(
        words, ["TITLE"], "below", stop_labels=["NUMBER", "REVISION"]
    )
    assert found is not None
    assert found[0] == "B2 - Combined Mechanical Layout - Apartment Type B2-2B"
    assert "2-04" not in found[0]
    assert "700" not in found[0]
    assert "1130" not in found[0]
