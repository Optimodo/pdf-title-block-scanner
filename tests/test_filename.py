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
    parsed = parse_filename("WCR-MBS-B7-XX-DR-M-5301 - B7 - Mechanical Services Layout_C01.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "WCR-MBS-B7-XX-DR-M-5301"
    assert parsed.title == "B7 - Mechanical Services Layout"
    assert parsed.revision == "C01"


def test_windows_copy_suffix_stripped():
    parsed = parse_filename("ABC-WXY-ZZ-00-DR-A-0001-P01 - Copy.pdf")
    assert parsed.parse_ok
    assert parsed.document_reference == "ABC-WXY-ZZ-00-DR-A-0001"
    assert parsed.revision == "P01"
