"""Toggleable QA checks for TBCheckCustom / --disable / --checks."""

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
ALIASES: dict[str, tuple[str, ...]] = {
    "all": CHECK_IDS,
    "portal": ("portal-revision", "portal-title"),
}


def all_check_ids() -> frozenset[str]:
    return frozenset(CHECK_IDS)


@dataclass
class CheckOptions:
    """Which policy checks are allowed to raise a status."""

    enabled: frozenset[str] = field(default_factory=all_check_ids)

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
        names = ALIASES.get(token)
        if names is None:
            if token not in CHECK_BY_ID:
                known = ", ".join(CHECK_IDS)
                aliases = ", ".join(sorted(ALIASES))
                raise UnknownCheckError(
                    f"Unknown check {token!r}. Known checks: {known}. Aliases: {aliases}."
                )
            names = (token,)
        for name in names:
            if name not in seen:
                seen.add(name)
                expanded.append(name)
    return expanded


def resolve_check_options(
    *,
    only: str | list[str] | None = None,
    disable: str | list[str] | None = None,
    enable: str | list[str] | None = None,
) -> CheckOptions:
    """Start from all checks, optionally replace with --checks, then disable/enable."""
    enabled = set(expand_check_names(only) if only else CHECK_IDS)
    for name in expand_check_names(disable):
        enabled.discard(name)
    for name in expand_check_names(enable):
        enabled.add(name)
    return CheckOptions(enabled=frozenset(enabled))


def parse_check_choice(raw: str) -> list[str]:
    """Resolve typed menu input: numbers (1-12), ids, and aliases."""
    tokens: list[str] = []
    for part in raw.replace(";", ",").replace(",", " ").split():
        token = _normalize_token(part)
        if not token:
            continue
        if token.isdigit():
            index = int(token)
            if index < 1 or index > len(QA_CHECKS):
                raise UnknownCheckError(
                    f"No check number {index}. Use 1-{len(QA_CHECKS)}."
                )
            tokens.append(QA_CHECKS[index - 1].id)
            continue
        tokens.append(token)
    return expand_check_names(tokens)


def format_check_menu(options: CheckOptions | None = None) -> str:
    options = options or CheckOptions()
    lines = [f"{len(QA_CHECKS)} QA checks that can be toggled:", ""]
    width = max(len(item.id) for item in QA_CHECKS)
    for index, item in enumerate(QA_CHECKS, start=1):
        mark = "ON " if options.allows(item.id) else "OFF"
        lines.append(f"  {index:2}. [{mark}] {item.id.ljust(width)}  {item.summary}")
    lines.append("")
    lines.append("Type a number, name, or alias (portal, all) to turn a check off or on.")
    lines.append("Press Enter with nothing typed to start the scan.")
    lines.append(_ALWAYS_ON)
    return "\n".join(lines)


def format_check_list() -> str:
    lines = ["QA checks (toggle with --disable / --enable / --checks, or the on-screen menu):", ""]
    width = max(len(item.id) for item in QA_CHECKS)
    for index, item in enumerate(QA_CHECKS, start=1):
        lines.append(f"  {index:2}. {item.id.ljust(width)}  {item.summary}")
    lines.append("")
    lines.append("Aliases: all, portal (portal-revision + portal-title)")
    lines.append(_ALWAYS_ON)
    lines.append("")
    lines.append("Examples:")
    lines.append("  TBCheckCustom.exe")
    lines.append("  TBCheckCustom.exe --disable portal-revision")
    lines.append("  TBCheckCustom.exe --disable portal")
    lines.append("  TBCheckCustom.exe --checks mismatch,spelling,client")
    lines.append("  TBCheckCustom.exe --disable all --enable history")
    return "\n".join(lines)
