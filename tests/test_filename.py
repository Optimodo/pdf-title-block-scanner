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
    assert parsed.revision == "C"
    assert parsed.title == "A-101 Rev"


def test_loose_title_and_revision_without_iso_core():
    parsed = parse_filename("Ground Floor GA_P01.pdf")
    assert not parsed.parse_ok
    assert parsed.document_reference is None
    assert parsed.revision == "P01"
    assert parsed.title == "Ground Floor GA"
