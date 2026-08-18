from drawing_qa.extract import take_until_label
from drawing_qa.models import Word


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


def test_take_until_label_keeps_all_when_no_heading():
    words = _words("Ground", "Floor", "GA")
    kept = take_until_label(words, ["REV"])
    assert [w.text for w in kept] == ["Ground", "Floor", "GA"]
