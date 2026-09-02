"""Entry point for TBCheckCustom — same QA run with CLI check toggles."""

import sys

from drawing_qa.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    args = ["--custom-checks"]
    if argv is not None:
        args.extend(argv)
    else:
        args.extend(sys.argv[1:])
    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
