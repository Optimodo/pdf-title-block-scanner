"""Build the standalone TBCheck executables with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "drawing_qa" / "default_config"
ENTRY = ROOT / "tbcheck.py"
ENTRY_RENAME = ROOT / "tbcheck_rename.py"


def build_executable(entry_script: Path, exe_name: str) -> int:
    """Build a single executable with PyInstaller.
    
    Args:
        entry_script: Path to entry point script
        exe_name: Name for the output executable
        
    Returns:
        Exit code
    """
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
        "PIL",
        "--add-data",
        add_data,
        str(entry_script),
    ]
    print(f"\nBuilding {exe_name}...")
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    """Build both TBCheck and TBCheckRename executables."""
    # Build standard TBCheck
    code = build_executable(ENTRY, "TBCheck")
    if code != 0:
        print(f"\nERROR: Failed to build TBCheck (exit code {code})")
        return code
    
    # Build auto-rename variant
    code = build_executable(ENTRY_RENAME, "TBCheckRename")
    if code != 0:
        print(f"\nERROR: Failed to build TBCheckRename (exit code {code})")
        return code
    
    print("\n✓ Both executables built successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
