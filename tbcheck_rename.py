#!/usr/bin/env python3
"""
TBCheckRename - Entry point for auto-rename variant.

This executable automatically renames files to include document reference,
title, and revision from the title block. No user prompt is given.
"""

import sys

from drawing_qa.cli_rename import main

if __name__ == "__main__":
    sys.exit(main())
