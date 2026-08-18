"""Build the standalone TBCheck executable with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "drawing_qa" / "default_config"
ENTRY = ROOT / "tbcheck.py"


def main() -> int:
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
        "TBCheck",
        "--collect-all",
        "pymupdf",
        "--hidden-import",
        "openpyxl",
        "--hidden-import",
        "yaml",
        "--add-data",
        add_data,
        str(ENTRY),
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
