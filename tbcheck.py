"""Drop-in entry point: check every PDF in this folder (PyInstaller target)."""

from drawing_qa.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
