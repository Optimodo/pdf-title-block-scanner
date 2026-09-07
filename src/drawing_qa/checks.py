"""Toggleable QA checks for QA-TB-Custom-Checker / --disable / --checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from drawing_qa.models import CheckStatus

_ALWAYS_ON = (
    "Extraction failures (UNDETECTED, INCOMPLETE, ERROR) stay on; they are not QA policy checks."
)


@dataclass(frozen=True)
class QaCheck:
    id: str
    status: CheckStatus
    summary: str


QA_CHECKS: tuple[QaCheck, ...] = (
    QaCheck(
        "mismatch",
        CheckStatus.MISMATCH,
        "Filename disagrees with the current title-block values",
    ),
    QaCheck(
        "history",
        CheckStatus.HISTORY_MISMATCH,
        "Current revision/status/date disagrees with the revision-history table",
    ),
    QaCheck(
        "spelling",
        CheckStatus.SPELLING_ERROR,
        "Possible spelling error in the title",
    ),
    QaCheck(
        "duplicates",
        CheckStatus.DUPLICATE_REFERENCE,
        "More than one PDF has the same document reference",
    ),
    QaCheck(
        "date-regression",
        CheckStatus.DATE_REGRESSION,
        "Later history revision has an earlier date",
    ),
    QaCheck(
        "suitability",
        CheckStatus.SUITABILITY_ERROR,
        "Purpose of issue is not on the project whitelist",
    ),
    QaCheck(
        "purpose",
        CheckStatus.PURPOSE_MISMATCH,
        "P revision with a construction purpose, or C revision with a review purpose",
    ),
    QaCheck(
        "dwg",
        CheckStatus.DWG_ISSUE,
        "DWG missing, or paired DWG uses different sheet-number punctuation",
    ),
    QaCheck(
        "portal-revision",
        CheckStatus.PORTAL_REVISION,
        "Revision is not the next issue after the portal document list",
    ),
    QaCheck(
        "portal-title",
        CheckStatus.PORTAL_TITLE,
        "Title disagrees with the portal document list",
    ),
    QaCheck(
        "client",
        CheckStatus.CLIENT_ERROR,
        "Title-block client name is missing or not on the project list",
    ),
    QaCheck(
        "filename-parse",
        CheckStatus.FILENAME_PARSE_ERROR,
        "Filename is not ISO 19650",
    ),
)

CHECK_IDS: tuple[str, ...] = tuple(item.id for item in QA_CHECKS)
CHECK_BY_ID: dict[str, QaCheck] = {item.id: item for item in QA_CHECKS}
REPORT_TOGGLES: tuple[tuple[str, str], ...] = (
    (
        "previews",
        "Show cropped title-block fields on every drawing in the Excel report",
    ),
)
REPORT_TOGGLE_IDS: frozenset[str] = frozenset(item[0] for item in REPORT_TOGGLES)
MENU_COUNT = len(QA_CHECKS) + len(REPORT_TOGGLES)
ALIASES: dict[str, tuple[str, ...]] = {
    "all": CHECK_IDS,
    "portal": ("portal-revision", "portal-title"),
}


def all_check_ids() -> frozenset[str]:
    return frozenset(CHECK_IDS)


@dataclass
class CheckOptions:
    """Which policy checks are allowed to raise a status, plus report toggles."""

    enabled: frozenset[str] = field(default_factory=all_check_ids)
    field_previews: bool = False

    def allows(self, check_id: str) -> bool:
        return check_id in self.enabled

    def disabled_ids(self) -> list[str]:
        return [item.id for item in QA_CHECKS if item.id not in self.enabled]


class UnknownCheckError(ValueError):
    pass


def _normalize_token(token: str) -> str:
    return token.strip().lower().replace("_", "-")


def _split_tokens(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return []
    chunks = [raw] if isinstance(raw, str) else list(raw)
    tokens: list[str] = []
    for chunk in chunks:
        for part in str(chunk).replace(";", ",").split(","):
            token = _normalize_token(part)
            if token:
                tokens.append(token)
    return tokens


def expand_check_names(raw: str | list[str] | None) -> list[str]:
    """Resolve comma-separated ids and aliases; raise on unknown names."""
    expanded: list[str] = []
    seen: set[str] = set()
    for token in _split_tokens(raw):
        if token in REPORT_TOGGLE_IDS:
            if token not in seen:
                seen.add(token)
                expanded.append(token)
            continue
        names = ALIASES.get(token)
        if names is None:
            if token not in CHECK_BY_ID:
                known = ", ".join(CHECK_IDS)
                extras = ", ".join(sorted(REPORT_TOGGLE_IDS))
                aliases = ", ".join(sorted(ALIASES))
                raise UnknownCheckError(
                    f"Unknown check {token!r}. Known checks: {known}. "
                    f"Report options: {extras}. Aliases: {aliases}."
                )
            names = (token,)
        for name in names:
            if name not in seen:
                seen.add(name)
                expanded.append(name)
    return expanded


def _split_report_toggles(names: list[str]) -> tuple[list[str], set[str]]:
    checks = [name for name in names if name not in REPORT_TOGGLE_IDS]
    extras = {name for name in names if name in REPORT_TOGGLE_IDS}
    return checks, extras


def resolve_check_options(
    *,
    only: str | list[str] | None = None,
    disable: str | list[str] | None = None,
    enable: str | list[str] | None = None,
) -> CheckOptions:
    """Start from all checks, optionally replace with --checks, then disable/enable."""
    field_previews = False
    if only:
        only_checks, only_extra = _split_report_toggles(expand_check_names(only))
        enabled = set(only_checks)
        field_previews = "previews" in only_extra
    else:
        enabled = set(CHECK_IDS)
    disable_checks, disable_extra = _split_report_toggles(expand_check_names(disable))
    for name in disable_checks:
        enabled.discard(name)
    if "previews" in disable_extra:
        field_previews = False
    enable_checks, enable_extra = _split_report_toggles(expand_check_names(enable))
    for name in enable_checks:
        enabled.add(name)
    if "previews" in enable_extra:
        field_previews = True
    return CheckOptions(enabled=frozenset(enabled), field_previews=field_previews)


def parse_check_choice(raw: str) -> list[str]:
    """Resolve typed menu input: numbers (1-12), ids, and aliases."""
    tokens: list[str] = []
    for part in raw.replace(";", ",").replace(",", " ").split():
        token = _normalize_token(part)
        if not token:
            continue
        if token.isdigit():
            index = int(token)
            if index < 1 or index > MENU_COUNT:
                raise UnknownCheckError(
                    f"No check number {index}. Use 1-{MENU_COUNT}."
                )
            if index <= len(QA_CHECKS):
                tokens.append(QA_CHECKS[index - 1].id)
            else:
                tokens.append(REPORT_TOGGLES[index - len(QA_CHECKS) - 1][0])
            continue
        tokens.append(token)
    return expand_check_names(tokens)


def format_check_menu(options: CheckOptions | None = None) -> str:
    options = options or CheckOptions()
    width = max(
        [len(item.id) for item in QA_CHECKS]
        + [len(item[0]) for item in REPORT_TOGGLES]
    )
    lines = [f"{len(QA_CHECKS)} QA checks that can be toggled:", ""]
    for index, item in enumerate(QA_CHECKS, start=1):
        mark = "ON " if options.allows(item.id) else "OFF"
        lines.append(f"  {index:2}. [{mark}] {item.id.ljust(width)}  {item.summary}")
    lines.append("")
    lines.append("Report options:")
    for offset, (toggle_id, summary) in enumerate(REPORT_TOGGLES, start=1):
        index = len(QA_CHECKS) + offset
        on = toggle_id == "previews" and options.field_previews
        mark = "ON " if on else "OFF"
        lines.append(f"  {index:2}. [{mark}] {toggle_id.ljust(width)}  {summary}")
    lines.append("")
    lines.append("Type a number, name, or alias (portal, all, previews) to turn an item off or on.")
    lines.append("Press Enter with nothing typed to start the scan.")
    lines.append(_ALWAYS_ON)
    return "\n".join(lines)


def format_check_list() -> str:
    from drawing_qa.version import TOOL_CUSTOM, versioned_exe_name

    exe = f"{versioned_exe_name(TOOL_CUSTOM)}.exe"
    width = max(
        [len(item.id) for item in QA_CHECKS]
        + [len(item[0]) for item in REPORT_TOGGLES]
    )
    lines = ["QA checks (toggle with --disable / --enable / --checks, or the on-screen menu):", ""]
    for index, item in enumerate(QA_CHECKS, start=1):
        lines.append(f"  {index:2}. {item.id.ljust(width)}  {item.summary}")
    lines.append("")
    lines.append("Report options:")
    for offset, (toggle_id, summary) in enumerate(REPORT_TOGGLES, start=1):
        index = len(QA_CHECKS) + offset
        lines.append(f"  {index:2}. {toggle_id.ljust(width)}  {summary}")
    lines.append("")
    lines.append("Aliases: all, portal (portal-revision + portal-title), previews")
    lines.append(_ALWAYS_ON)
    lines.append("")
    lines.append("Examples:")
    lines.append(f"  {exe}")
    lines.append(f"  {exe} --disable portal-revision")
    lines.append(f"  {exe} --disable portal")
    lines.append(f"  {exe} --enable previews")
    lines.append(f"  {exe} --checks mismatch,spelling,client")
    lines.append(f"  {exe} --disable all --enable history")
    return "\n".join(lines)
