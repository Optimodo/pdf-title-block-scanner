"""Entry point for TBCheckRename - auto-rename variant.

This module provides an entry point that automatically sets flags for
renaming files with full details (document reference + title + revision).
"""

import sys

from drawing_qa.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    """Run QA check with auto-rename enabled (including title and revision).
    
    Args:
        argv: Command-line arguments (default: sys.argv[1:])
        
    Returns:
        Exit code
    """
    # Prepare arguments with auto-rename flags
    args = ["--auto-rename", "--include-title", "--include-revision"]
    
    # Append user-provided arguments
    if argv is not None:
        args.extend(argv)
    else:
        args.extend(sys.argv[1:])
    
    # Run with modified arguments
    return cli_main(args)


if __name__ == "__main__":
    sys.exit(main())
