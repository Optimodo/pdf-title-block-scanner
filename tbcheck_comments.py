"""Drop-in entry point: copy commented PDFs into Sorted/{revision}."""

from drawing_qa.cli_comments import main

if __name__ == "__main__":
    raise SystemExit(main())
