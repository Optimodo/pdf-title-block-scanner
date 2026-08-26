from drawing_qa.history import detect_revision_history
from drawing_qa.models import Word
from drawing_qa.tokens import parse_date, revision_rank, suitability_code


def _w(x, y, text, width=40) -> Word:
    return Word(x0=x, y0=y, x1=x + width, y1=y + 8, text=text)


def test_revision_rank_orders_iso_codes():
    assert revision_rank("P01") < revision_rank("P02") < revision_rank("C01")


def test_parse_uk_and_iso_dates():
    assert parse_date("15.06.24") == parse_date("15/06/2024")
    assert parse_date("2024-06-15") == parse_date("15 Jun 2024")


def test_invalid_calendar_dates_still_compare_equal():
    from drawing_qa.tokens import dates_equal

    assert dates_equal("30.02.26", "30/02/2026") is True
    assert dates_equal("30.02.26", "24.03.26") is False


def test_suitability_code():
    assert suitability_code("S4 - Construction") == "S4"
    assert suitability_code("S3 Review and Comment") == "S3"
    assert suitability_code("A - CONSTRUCTION") == "A"


def test_suitability_codes_are_not_revision_tokens():
    from drawing_qa.tokens import is_revision_token, normalize_revision_token

    assert is_revision_token("P03")
    assert is_revision_token("C02")
    assert is_revision_token("С02")  # Cyrillic Es, looks like C
    assert normalize_revision_token("С02") == "C02"
    assert not is_revision_token("S5")
    assert not is_revision_token("S3")
    assert not is_revision_token("A1")


def test_history_cyrillic_c_revision_is_not_read_as_suitability():
    words = [
        _w(10, 30, "С02", 30),
        _w(50, 30, "S5", 20),
        _w(80, 30, "-", 8),
        _w(90, 30, "Revised", 40),
        _w(200, 30, "21.08.26", 50),
        _w(10, 50, "P02", 30),
        _w(50, 50, "S3", 20),
        _w(80, 50, "Issued", 40),
        _w(200, 50, "05.06.26", 50),
        _w(10, 70, "Amendments", 60),
    ]
    history = detect_revision_history(words)
    assert history.latest is not None
    assert history.latest.revision == "C02"
    assert history.latest.date == "21.08.26"
    assert history.latest.suitability and history.latest.suitability.startswith("S5")
    assert [row.revision for row in history.rows] == ["C02", "P02"]


def test_history_latest_follows_newest_date_when_p_follows_c():
    words = [
        _w(10, 30, "P03"),
        _w(50, 30, "21.08.26"),
        _w(10, 50, "C02"),
        _w(50, 50, "11.08.26"),
        _w(10, 70, "P02"),
        _w(50, 70, "29.05.26"),
        _w(10, 90, "Amendments", 60),
    ]
    history = detect_revision_history(words)
    assert history.latest is not None
    assert history.latest.revision == "P03"


def test_extract_suitability_keeps_description_before_or_after_code():
    from drawing_qa.tokens import extract_suitability

    assert extract_suitability("Suitable For Tender S2") == "S2 - Suitable For Tender"
    assert extract_suitability("S3 - Review & Comment") == "S3 - Review & Comment"
    assert extract_suitability("REVIEW & COMMENT S3") == "S3 - REVIEW & COMMENT"
    assert extract_suitability("S2") == "S2"
    assert extract_suitability("CONSTRUCTION A") == "A - CONSTRUCTION"
    assert extract_suitability("A CONSTRUCTION Designed by MG") == "A - CONSTRUCTION"
    assert extract_suitability("C01 01.06.2026 A - For Construction MT") == (
        "A - For Construction"
    )
    assert extract_suitability("+ CONSTRUCTION S5 Void 20,25") == "S5 - CONSTRUCTION"
    assert extract_suitability("+ Review & Comment S3 Void 20,25") == (
        "S3 - Review & Comment"
    )


def test_date_in_text_does_not_treat_void_notes_as_dates():
    from drawing_qa.tokens import DATE_IN_TEXT

    assert DATE_IN_TEXT.search("S5 Void 20,25") is None
    assert DATE_IN_TEXT.search("15 Jun 2024") is not None


def test_history_picks_latest_not_first_row():
    words = [
        _w(10, 10, "REV", 20),
        _w(50, 10, "DATE", 20),
        _w(10, 30, "P01"),
        _w(50, 30, "12.01.24"),
        _w(120, 30, "First"),
        _w(10, 50, "P02"),
        _w(50, 50, "03.03.24"),
        _w(120, 50, "Updated"),
        _w(10, 70, "P03"),
        _w(50, 70, "15.06.24"),
        _w(120, 70, "Construction"),
    ]
    history = detect_revision_history(words)
    assert history.latest is not None
    assert history.latest.revision == "P03"
    assert history.latest.date == "15.06.24"
    assert history.first is not None
    assert history.first.revision == "P01"
    assert history.first.date == "12.01.24"
    assert len(history.rows) == 3


def test_amendments_heading_allows_single_history_row():
    words = [
        _w(10, 30, "P01", 30),
        _w(50, 30, "14.08.26", 50),
        _w(120, 30, "S3", 20),
        _w(150, 30, "Review", 40),
        _w(10, 55, "Rev", 20),
        _w(50, 55, "Date", 20),
        _w(80, 80, "Amendments", 60),
    ]
    history = detect_revision_history(words)
    assert history.latest is not None
    assert history.latest.revision == "P01"
    assert history.latest.date == "14.08.26"
    assert history.latest.suitability and history.latest.suitability.startswith("S3")


def test_history_picks_latest_when_newest_is_on_top():
    words = [
        _w(10, 30, "P03"),
        _w(50, 30, "15.06.24"),
        _w(10, 50, "P02"),
        _w(50, 50, "03.03.24"),
        _w(10, 70, "P01"),
        _w(50, 70, "12.01.24"),
    ]
    history = detect_revision_history(words)
    assert history.latest is not None
    assert history.latest.revision == "P03"
    assert history.first is not None
    assert history.first.revision == "P01"
    assert history.first.date == "12.01.24"


def test_history_first_uses_p01_when_date_is_not_a_real_calendar_day():
    words = [
        _w(10, 30, "C01"),
        _w(50, 30, "06.08.26"),
        _w(10, 50, "P02"),
        _w(50, 50, "24.03.26"),
        _w(10, 70, "P01"),
        _w(50, 70, "30.02.26"),
        _w(10, 90, "Amendments", 60),
    ]
    history = detect_revision_history(words)
    assert history.first is not None
    assert history.first.revision == "P01"
    assert history.first.date == "30.02.26"


def test_history_folds_wrapped_description_onto_previous_row():
    words = [
        _w(10, 30, "P02"),
        _w(50, 30, "24.03.26"),
        _w(120, 30, "Bulkhead"),
        _w(120, 42, "Lighting"),
        _w(180, 42, "updated"),
        _w(10, 60, "P01"),
        _w(50, 60, "12.01.24"),
        _w(120, 60, "First"),
        _w(10, 80, "Amendments", 60),
    ]
    history = detect_revision_history(words)
    assert [row.revision for row in history.rows] == ["P02", "P01"]
    p02 = next(row for row in history.rows if row.revision == "P02")
    assert "Lighting" in (p02.description or "")
