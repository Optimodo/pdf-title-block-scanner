"""Drop-in entry point: QA with command-line check toggles (PyInstaller target)."""

from drawing_qa.cli_custom import main

if __name__ == "__main__":
    raise SystemExit(main())
