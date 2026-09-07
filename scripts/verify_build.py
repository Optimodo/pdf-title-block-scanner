from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(title: str, args: list[str]) -> None:
    print(f"\n== {title} ==", flush=True)
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    run("pytest", [sys.executable, "-m", "pytest", "-q"])
    run("PyInstaller", [sys.executable, str(ROOT / "scripts" / "build_exe.py")])
    sys.path.insert(0, str(ROOT / "src"))
    from drawing_qa.version import TOOL_CHECKER, versioned_exe_name

    built = versioned_exe_name(TOOL_CHECKER)
    exe = ROOT / "dist" / (f"{built}.exe" if sys.platform == "win32" else built)
    if not exe.is_file():
        print(f"ERROR: expected build output at {exe}", file=sys.stderr)
        return 1
    print(f"\nBuilt {exe} ({exe.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
