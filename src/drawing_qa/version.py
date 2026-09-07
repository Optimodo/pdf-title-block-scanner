"""User-facing tool names and a short version for exe filenames and banners."""

from __future__ import annotations

__version__ = "1.0"

TOOL_CHECKER = "QA-TB-Checker"
TOOL_CUSTOM = "QA-TB-Custom-Checker"
TOOL_RENAMER = "QA-TB-File-Renamer"


def versioned_exe_name(tool: str) -> str:
    """QA-TB-Checker-v1.0 — dashes, short version so a newer copy is obvious."""
    return f"{tool}-v{__version__}"


def tool_banner(tool: str) -> str:
    return f"{tool} v{__version__}"
