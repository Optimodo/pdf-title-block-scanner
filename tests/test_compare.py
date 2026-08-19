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
    _comps, _hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MISMATCH


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
    _comps, _hist, status, _notes = compare_document(filename, titleblock, DEFAULT_RULES)
    assert status == CheckStatus.MISMATCH


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
