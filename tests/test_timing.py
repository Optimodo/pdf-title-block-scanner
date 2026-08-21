from drawing_qa.timing import add, configure, format_report, is_enabled, reset, span


def test_timing_disabled_is_a_noop():
    configure(False)
    assert is_enabled() is False
    add("extract_words", 1.5)
    with span("preview"):
        pass
    assert format_report() == ""


def test_timing_enabled_records_spans():
    configure(True)
    try:
        add("extract_words", 1.0)
        add("extract_words", 1.0)
        with span("preview"):
            pass
        report = format_report()
        assert "extract_words" in report
        assert "2x" in report
        assert "preview" in report
    finally:
        configure(False)
        reset()
