from drawing_qa.version import (
    TOOL_CHECKER,
    TOOL_CUSTOM,
    TOOL_RENAMER,
    __version__,
    tool_banner,
    versioned_exe_name,
)


def test_exe_names_use_dashes_and_short_version():
    assert "-" in TOOL_CHECKER
    assert "_" not in TOOL_CHECKER
    assert versioned_exe_name(TOOL_CHECKER) == f"QA-TB-Checker-v{__version__}"
    assert versioned_exe_name(TOOL_CUSTOM) == f"QA-TB-Custom-Checker-v{__version__}"
    assert versioned_exe_name(TOOL_RENAMER) == f"QA-TB-File-Renamer-v{__version__}"
    assert tool_banner(TOOL_CHECKER) == f"QA-TB-Checker v{__version__}"
