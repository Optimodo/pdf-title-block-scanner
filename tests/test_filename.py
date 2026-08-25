from drawing_qa.filename import parse_filename


def test_iso19650_reference_and_revision():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001-P01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.parts["role"] == "A"
    assert parsed.parts["number"] == "0001"
    assert parsed.revision == "P01"
    assert parsed.title is None


def test_iso19650_with_title_and_revision():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001_Ground Floor GA_C02.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.title == "Ground Floor GA"
    assert parsed.revision == "C02"


def test_iso19650_reference_only():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.revision is None
    assert parsed.title is None


def test_lowercase_is_normalised():
    parsed = parse_filename("abc-wxy-zz-00-dr-a-0001-p01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.revision == "P01"


def test_hyphenated_title_does_not_steal_ga_as_revision():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001-Ground-Floor-GA.pdf")
    assert parsed.parse_ok
    assert parsed.revision is None
    assert parsed.title == "Ground-Floor-GA"


def test_rejects_non_iso_name():
    parsed = parse_filename("A-101 Rev C.pdf")
    assert not parsed.parse_ok
    assert parsed.document_reference is None
    assert parsed.revision is None
    assert parsed.title is None


def test_trailing_revision_without_iso_core():
    parsed = parse_filename("Ground Floor GA_P01.pdf")
    assert not parsed.parse_ok
    assert parsed.document_reference is None
    assert parsed.revision == "P01"
    assert parsed.title is None


def test_compound_document_number_and_export_date_suffix():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-675-001-260717-WMS.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-675-001"
    assert parsed.parts["number"] == "675-001"
    assert parsed.revision is None


def test_title_then_trailing_revision():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001 - Ground Floor GA - P01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.title == "Ground Floor GA"
    assert parsed.revision == "P01"


def test_building_code_in_title_is_not_treated_as_revision():
    parsed = parse_filename(
        "WCR-MBS-B7-XX-DR-M-5301 - B7 - Mechanical Services Layout_C01.pdf"
    )
    assert parsed.parse_ok
    assert parsed.document_reference == "WCR-MBS-B7-XX-DR-M-5301"
    assert parsed.title == "B7 - Mechanical Services Layout"
    assert parsed.revision == "C01"


def test_windows_copy_suffix_stripped():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001-P01 - Copy.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.revision == "P01"


def test_underscore_title_keeps_internal_dashes():
    parsed = parse_filename(
        "R456-MAL20-BI-00-DR-W-655-002_Block I - SVP&RWP Services Drawing - Level 00_P01.pdf"
    )
    assert parsed.parse_ok
    assert parsed.document_reference == "R456-MAL20-BI-00-DR-W-655-002"
    assert parsed.title == "Block I - SVP&RWP Services Drawing - Level 00"
    assert parsed.revision == "P01"


def test_title_with_level_range_dashes_and_space_dash_separators():
    parsed = parse_filename(
        "R456-MAL20-BI-ZZ-DR-W-655-005 - Block I - SVP&RWP Services Drawing - Level 03-13 - P01.pdf"
    )
    assert parsed.parse_ok
    assert parsed.document_reference == "R456-MAL20-BI-ZZ-DR-W-655-005"
    assert parsed.title == "Block I - SVP&RWP Services Drawing - Level 03-13"
    assert parsed.revision == "P01"


def test_underscore_title_with_level_range_and_revision():
    parsed = parse_filename(
        "R456-MAL20-BI-ZZ-DR-W-655-005_Block I - SVP&RWP Services Drawing - Level 03-13_P01.pdf"
    )
    assert parsed.parse_ok
    assert parsed.document_reference == "R456-MAL20-BI-ZZ-DR-W-655-005"
    assert parsed.title == "Block I - SVP&RWP Services Drawing - Level 03-13"
    assert parsed.revision == "P01"


def test_title_only_after_doc_ref():
    parsed = parse_filename(
        "R456-MAL20-BI-ZZ-DR-W-655-005 - Block I - SVP&RWP Services Drawing - Level 03-13.pdf"
    )
    assert parsed.parse_ok
    assert parsed.document_reference == "R456-MAL20-BI-ZZ-DR-W-655-005"
    assert parsed.title == "Block I - SVP&RWP Services Drawing - Level 03-13"
    assert parsed.revision is None


def test_revision_only_after_compound_doc_ref():
    parsed = parse_filename("R456-MAL20-BI-ZZ-DR-W-655-005_P01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "R456-MAL20-BI-ZZ-DR-W-655-005"
    assert parsed.title is None
    assert parsed.revision == "P01"


def test_seven_block_doc_ref_with_underscore_title():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001_Ground Floor - GA_P01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.title == "Ground Floor - GA"
    assert parsed.revision == "P01"


def test_dotted_sheet_suffix_stays_on_document_number():
    parsed = parse_filename(
        "R459-MBS-DZ-ZZ-DR-W-51333.1 - BLOCK D APARTMENT TYPE E1 MECHANICAL PIPEWORK LAYOUT.pdf"
    )
    assert parsed.parse_ok
    assert parsed.document_reference == "R459-MBS-DZ-ZZ-DR-W-51333.1"
    assert parsed.parts["number"] == "51333.1"
    assert parsed.title == "BLOCK D APARTMENT TYPE E1 MECHANICAL PIPEWORK LAYOUT"
    assert parsed.revision is None


def test_dotted_sheet_suffix_with_revision_and_not_in_title():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001.2_P01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001.2"
    assert parsed.parts["number"] == "0001.2"
    assert parsed.revision == "P01"
    assert parsed.title is None


def test_dotted_and_hyphen_sheet_suffixes_are_the_same_drawing():
    from drawing_qa.docref import canonical_doc_ref, sheet_suffix_style

    dotted = parse_filename("R459-MBS-DZ-ZZ-DR-W-51333.1.pdf")
    hyphen = parse_filename("R459-MBS-DZ-ZZ-DR-W-51333-1.pdf")
    assert dotted.document_reference == "R459-MBS-DZ-ZZ-DR-W-51333.1"
    assert hyphen.document_reference == "R459-MBS-DZ-ZZ-DR-W-51333-1"
    assert canonical_doc_ref(dotted.document_reference) == canonical_doc_ref(
        hyphen.document_reference
    )
    assert sheet_suffix_style(dotted.document_reference) == "dot"
    assert sheet_suffix_style(hyphen.document_reference) == "hyphen"
