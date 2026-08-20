#!/usr/bin/env python3
"""TBCheckRename — PyInstaller-friendly wrapper (same as tbcheck_rename.py)."""

import sys

from drawing_qa.cli_rename import main

if __name__ == "__main__":
    sys.exit(main())
