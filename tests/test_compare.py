from drawing_qa.compare import compare_document
from drawing_qa.models import CheckStatus, FilenameFields, HistoryRow, RevisionHistory, TitleBlockFields


DEFAULT_RULES = {
    "document_reference": "required",
    "revision": "if_both_present",
    "title": "if_both_present",
    "suitability": "if_both_present",
    "date": "if_both_present",
}


def test_match_when_required_fields_agree():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        title=None,
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        title="Ground Floor GA",
    )
    _comps, _hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MATCH


def test_missing_filename_revision_and_title_are_not_incomplete():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision=None,
        title=None,
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        title="Ground Floor GA",
    )
    _comps, _hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MATCH


def test_mismatch_on_revision():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P02",
    )
    _comps, _hist, status, notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MISMATCH
    assert any("revision mismatch" in note.lower() for note in notes)


def test_title_compared_only_when_both_present():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        title="Ground Floor GA",
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        title="First Floor GA",
    )
    _comps, _hist, status, notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MISMATCH
    assert any("title mismatch" in note.lower() for note in notes)


def test_non_iso_filename_still_extracts_titleblock():
    filename = FilenameFields(
        raw_stem="A-101",
        document_reference=None,
        revision=None,
        parse_ok=False,
        notes=["Filename does not start with 7 hyphen-separated ISO 19650 fields"],
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P01",
        title="Ground Floor GA",
    )
    comparisons, _hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.FILENAME_PARSE_ERROR
    doc = next(item for item in comparisons if item.name == "document_reference")
    assert doc.titleblock_value == "ABC-WXY-ZZ-00-DR-A-0001"
    assert doc.filename_value is None
    assert doc.matched is None


def test_history_mismatch_when_latest_rev_differs():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P03",
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P03",
        date="15.06.24",
        history=RevisionHistory(
            rows=[],
            latest=HistoryRow(revision="P02", date="03.03.24"),
        ),
    )
    _comps, hist, status, notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.HISTORY_MISMATCH
    rev = next(item for item in hist if item.name == "history_revision")
    assert rev.matched is False
    assert any("P02" in note for note in notes)


def _p03_history() -> RevisionHistory:
    p01 = HistoryRow(revision="P01", date="12.01.24")
    p02 = HistoryRow(revision="P02", date="03.03.24")
    p03 = HistoryRow(revision="P03", date="15.06.24")
    return RevisionHistory(rows=[p01, p02, p03], latest=p03, first=p01)


def test_history_date_accepts_original_issue_or_latest():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P03",
        parse_ok=True,
    )
    history = _p03_history()
    for date in ("12.01.24", "15.06.24"):
        titleblock = TitleBlockFields(
            layout_id="bottom_right",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="P03",
            date=date,
            history=history,
        )
        _comps, hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
        assert status == CheckStatus.MATCH, date
        date_item = next(item for item in hist if item.name == "history_date")
        assert date_item.matched is True


def test_history_date_accepts_invalid_calendar_original_issue():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="C01",
        parse_ok=True,
    )
    p01 = HistoryRow(revision="P01", date="30.02.26")
    p02 = HistoryRow(revision="P02", date="24.03.26")
    c01 = HistoryRow(revision="C01", date="06.08.26")
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="C01",
        date="30/02/2026",
        history=RevisionHistory(rows=[p01, p02, c01], latest=c01, first=p01),
    )
    _comps, hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MATCH
    date_item = next(item for item in hist if item.name == "history_date")
    assert date_item.matched is True


def test_history_date_flags_when_neither_first_nor_latest():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P03",
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="P03",
        date="03.03.24",
        history=_p03_history(),
    )
    _comps, hist, status, notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.HISTORY_MISMATCH
    date_item = next(item for item in hist if item.name == "history_date")
    assert date_item.matched is False
    assert any("neither" in note for note in notes)


def test_mismatch_status_label_names_the_field():
    from pathlib import Path

    from drawing_qa.compare import build_result
    from drawing_qa.models import DocumentResult

    result = DocumentResult(
        path=Path("sheet.pdf"),
        filename=FilenameFields(
            raw_stem="x",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="P01",
            title="Ground Floor GA",
            parse_ok=True,
        ),
        titleblock=TitleBlockFields(
            layout_id="bottom_right",
            document_reference="ABC-WXY-ZZ-00-DR-A-0001",
            revision="P01",
            title="First Floor GA",
        ),
    )
    result = build_result(result, DEFAULT_RULES)
    assert result.status == CheckStatus.MISMATCH
    assert result.status_label() == "MISMATCH: TITLE"
    assert any("title mismatch" in note.lower() for note in result.notes)


def test_dotted_and_hyphen_document_numbers_match():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="R459-MBS-DZ-ZZ-DR-W-51333.1",
        revision="C01",
        parse_ok=True,
    )
    titleblock = TitleBlockFields(
        layout_id="mbs_right",
        document_reference="R459-MBS-DZ-ZZ-DR-W-51333-1",
        revision="C01",
        title="Block D",
    )
    _comps, _hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MATCH


OVAL_PURPOSES = [
    "S3 - For Review & Comment",
    "S4 - For Stage Approval",
    "S5 - For Construction",
]


def test_history_note_is_not_compared_to_current_purpose():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="C01",
        parse_ok=True,
    )
    latest = HistoryRow(
        revision="C01",
        date="15.06.24",
        suitability="S3 - Bathroom first fix",
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="C01",
        date="15.06.24",
        suitability="S5 - For Construction",
        history=RevisionHistory(rows=[latest], latest=latest, first=latest),
    )
    _comps, hist, status, _notes = compare_document(
        filename,
        titleblock,
        DEFAULT_RULES,
        allowed_suitability=OVAL_PURPOSES,
    )
    assert status == CheckStatus.MATCH
    suit = next(item for item in hist if item.name == "history_suitability")
    assert suit.matched is True
    assert "note" in (suit.detail or "").lower()


def test_history_whitelist_status_must_match_current_purpose():
    filename = FilenameFields(
        raw_stem="x",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="C01",
        parse_ok=True,
    )
    latest = HistoryRow(
        revision="C01",
        date="15.06.24",
        suitability="S4 - For Stage Approval",
    )
    titleblock = TitleBlockFields(
        layout_id="bottom_right",
        document_reference="ABC-WXY-ZZ-00-DR-A-0001",
        revision="C01",
        date="15.06.24",
        suitability="S5 - For Construction",
        history=RevisionHistory(rows=[latest], latest=latest, first=latest),
    )
    _comps, hist, status, notes = compare_document(
        filename,
        titleblock,
        DEFAULT_RULES,
        allowed_suitability=OVAL_PURPOSES,
    )
    assert status == CheckStatus.HISTORY_MISMATCH
    suit = next(item for item in hist if item.name == "history_suitability")
    assert suit.matched is False
    assert any("S4" in note for note in notes)
