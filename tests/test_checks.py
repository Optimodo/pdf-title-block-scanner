from drawing_qa.checks import (
    UnknownCheckError,
    format_check_list,
    resolve_check_options,
)


def test_disable_portal_revision_keeps_other_checks():
    options = resolve_check_options(disable="portal-revision")
    assert not options.allows("portal-revision")
    assert options.allows("portal-title")
    assert options.allows("mismatch")
    assert options.disabled_ids() == ["portal-revision"]


def test_disable_portal_alias_turns_off_revision_and_title():
    options = resolve_check_options(disable=["portal"])
    assert not options.allows("portal-revision")
    assert not options.allows("portal-title")
    assert options.allows("spelling")


def test_checks_only_then_enable():
    options = resolve_check_options(only="mismatch,spelling", enable="client")
    assert options.allows("mismatch")
    assert options.allows("spelling")
    assert options.allows("client")
    assert not options.allows("portal-revision")
    assert not options.allows("history")


def test_disable_all_then_enable_history():
    options = resolve_check_options(disable="all", enable="history")
    assert options.allows("history")
    assert not options.allows("mismatch")
    assert options.disabled_ids()


def test_unknown_check_raises():
    try:
        resolve_check_options(disable="not-a-check")
    except UnknownCheckError as exc:
        assert "not-a-check" in str(exc)
        return
    raise AssertionError("expected UnknownCheckError")


def test_parse_check_choice_accepts_numbers_and_alias():
    from drawing_qa.checks import parse_check_choice

    assert parse_check_choice("9") == ["portal-revision"]
    assert parse_check_choice("9,10") == ["portal-revision", "portal-title"]
    assert parse_check_choice("portal") == ["portal-revision", "portal-title"]


def test_list_checks_mentions_portal_revision():
    text = format_check_list()
    assert "portal-revision" in text
    assert "--disable portal-revision" in text
