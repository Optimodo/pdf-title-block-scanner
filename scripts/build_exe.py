"""Build the standalone QA-TB executables with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "drawing_qa" / "default_config"
ENTRY = ROOT / "tbcheck.py"
ENTRY_RENAME = ROOT / "tbcheck_rename.py"
ENTRY_CUSTOM = ROOT / "tbcheck_custom.py"

sys.path.insert(0, str(ROOT / "src"))
from drawing_qa.version import (  # noqa: E402
    TOOL_CHECKER,
    TOOL_CUSTOM,
    TOOL_RENAMER,
    versioned_exe_name,
)


def build_executable(entry_script: Path, exe_name: str) -> int:
    """Build a single executable with PyInstaller."""
    sep = ";" if sys.platform == "win32" else ":"
    add_data = f"{CONFIG}{sep}drawing_qa/default_config"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        exe_name,
        "--collect-all",
        "pymupdf",
        "--hidden-import",
        "openpyxl",
        "--hidden-import",
        "yaml",
        "--hidden-import",
        "PIL",
        "--hidden-import",
        "spellchecker",
        "--collect-all",
        "spellchecker",
        "--collect-all",
        "PIL",
        "--add-data",
        add_data,
        str(entry_script),
    ]
    print(f"\nBuilding {exe_name}...")
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    """Build the three versioned QA-TB executables."""
    targets = (
        (ENTRY, versioned_exe_name(TOOL_CHECKER)),
        (ENTRY_RENAME, versioned_exe_name(TOOL_RENAMER)),
        (ENTRY_CUSTOM, versioned_exe_name(TOOL_CUSTOM)),
    )
    for entry, name in targets:
        code = build_executable(entry, name)
        if code != 0:
            print(f"\nERROR: Failed to build {name} (exit code {code})")
            return code

    try:
        print("\n✓ All three executables built successfully")
    except UnicodeEncodeError:
        print("\nOK: All three executables built successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
