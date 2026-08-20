#!/usr/bin/env python3
"""
TBCheckRename - Automated QA check with full filename renaming.

This variant automatically renames files to include the document reference,
title, and revision from the title block. No user prompt is given for renaming.

Intended for use as a standalone executable for standardizing file naming.
"""

import sys

from drawing_qa.cli import main


if __name__ == "__main__":
    # Inject flags to enable auto-rename with title and revision
    args = ["--auto-rename", "--include-title", "--include-revision"]
    
    # Append any user-provided arguments
    args.extend(sys.argv[1:])
    
    # Run with modified arguments
    sys.exit(main(args))
