from drawing_qa.compare import compare_document
from drawing_qa.models import CheckStatus, FilenameFields, TitleBlockFields


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
    _comparisons, status, _notes = compare_document(
        filename,
        titleblock,
        {
            "document_reference": "required",
            "revision": "required",
            "title": "if_both_present",
        },
    )
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
    _comparisons, status, _notes = compare_document(
        filename,
        titleblock,
        {"document_reference": "required", "revision": "required", "title": "if_both_present"},
    )
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
    _comparisons, status, _notes = compare_document(
        filename,
        titleblock,
        {"document_reference": "required", "revision": "required", "title": "if_both_present"},
    )
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
    comparisons, status, _notes = compare_document(
        filename,
        titleblock,
        {"document_reference": "required", "revision": "required", "title": "if_both_present"},
    )
    assert status == CheckStatus.FILENAME_PARSE_ERROR
    doc = next(item for item in comparisons if item.name == "document_reference")
    assert doc.titleblock_value == "ABC-WXY-ZZ-00-DR-A-0001"
    assert doc.filename_value is None
    assert doc.matched is None
