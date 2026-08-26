from __future__ import annotations

import re
import sys
from pathlib import Path

REPORT_NAME = "TBCheckReport.xlsx"
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Folder that contains the exe (frozen) or the current working directory (source)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def bundled_config_dir() -> Path:
    """Default layouts shipped inside the package or the frozen exe."""
    if is_frozen():
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        for candidate in (
            meipass / "drawing_qa" / "default_config",
            meipass / "default_config",
            meipass / "config",
        ):
            if (candidate / "settings.yaml").is_file():
                return candidate
    return Path(__file__).resolve().parent / "default_config"


def resolve_config_dir(folder: Path | None = None, override: Path | None = None) -> Path:
    """Prefer a `config/` folder next to the exe; otherwise use bundled defaults."""
    if override is not None:
        return override
    base = folder if folder is not None else app_dir()
    sidecar = base / "config"
    if (sidecar / "settings.yaml").is_file():
        return sidecar
    return bundled_config_dir()


def sanitize_filename_part(text: str, fallback: str = "Drawings") -> str:
    """Strip characters Windows will not allow in a file name."""
    cleaned = _INVALID_FILENAME_CHARS.sub(" ", text)
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip(" .")
    return cleaned or fallback


def designer_report_path(main: Path) -> Path:
    """Sidecar workbook: {stem}_designer.xlsx next to the main report."""
    return main.with_name(f"{main.stem}_designer{main.suffix}")


def next_available_report_path(folder: Path, filename: str = REPORT_NAME) -> Path:
    """Return name.xlsx, then name-1.xlsx, name-2.xlsx, ... matching mbs-file-tools."""
    folder = folder.resolve()
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    primary = folder / f"{stem}{suffix}"
    if not primary.exists():
        return primary
    n = 1
    while True:
        candidate = folder / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def next_available_paired_report_path(folder: Path, stem: str) -> Path:
    """Next {stem}.xlsx that does not collide with an existing designer sidecar."""
    folder = folder.resolve()
    n = 0
    while True:
        suffix = "" if n == 0 else f"-{n}"
        main = folder / f"{stem}{suffix}.xlsx"
        designer = designer_report_path(main)
        if not main.exists() and not designer.exists():
            return main
        n += 1


def is_versioned_report_name(entry_name: str, template_filename: str = REPORT_NAME) -> bool:
    stem, ext = Path(template_filename.lower()).stem, Path(template_filename.lower()).suffix
    name = entry_name.lower()
    if name == f"{stem}{ext}":
        return True
    return re.fullmatch(re.escape(stem) + r"-\d+" + re.escape(ext), name) is not None
