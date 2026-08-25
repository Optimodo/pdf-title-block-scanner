from __future__ import annotations

import re
from datetime import date, datetime

REV_TOKEN = re.compile(r"^(?:[PC]\d{2}|[A-Z]\d?)$", re.IGNORECASE)
_PC_REVISION = re.compile(r"^[PC]\d{1,2}$", re.IGNORECASE)
SUITABILITY_TOKEN = re.compile(r"^(?:S[0-7]|A[0-9]|B[0-9]|CR)$", re.IGNORECASE)
# CAD fonts sometimes emit Cyrillic letters that look like Latin C/P in C01/P01.
_LATIN_LOOKALIKES = str.maketrans(
    {
        "\u0410": "A",
        "\u0430": "A",
        "\u0412": "B",
        "\u0432": "B",
        "\u0421": "C",
        "\u0441": "C",
        "\u0415": "E",
        "\u0435": "E",
        "\u041d": "H",
        "\u043d": "H",
        "\u041a": "K",
        "\u043a": "K",
        "\u041c": "M",
        "\u043c": "M",
        "\u041e": "O",
        "\u043e": "O",
        "\u0420": "P",
        "\u0440": "P",
        "\u0422": "T",
        "\u0442": "T",
        "\u0425": "X",
        "\u0445": "X",
    }
)
DATE_TOKEN = re.compile(
    r"^("
    r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}\s*[A-Za-z]{3,9}\s*\d{2,4}"
    r")$"
)
DATE_IN_TEXT = re.compile(
    r"(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})",
    re.IGNORECASE,
)
SUITABILITY_IN_TEXT = re.compile(
    r"\b(S[0-7]|A[0-9]|B[0-9]|CR)\b",
    re.IGNORECASE,
)
# Cut neighbouring title-block roles out of a suitability capture.
_SUITABILITY_TAIL = re.compile(
    r"\b(?:DESIGNED|DRAWN|CHECKED|APPROVED|AUTHORI[SZ]ED|VERIFIED)\b",
    re.IGNORECASE,
)
_TRAILING_INITIALS = re.compile(
    r"(?:\s+[A-Z](?:\.[A-Z])+\.?|\s+[A-Z]{2,3}\.?)$",
)
MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def fold_latin_lookalikes(text: str) -> str:
    return text.translate(_LATIN_LOOKALIKES)


def normalize_revision_token(text: str) -> str:
    return fold_latin_lookalikes(text.strip()).upper()


def is_revision_token(text: str) -> bool:
    token = normalize_revision_token(text)
    if not REV_TOKEN.fullmatch(token):
        return False
    return not SUITABILITY_TOKEN.fullmatch(token)


def is_pc_revision(text: str) -> bool:
    return bool(_PC_REVISION.fullmatch(normalize_revision_token(text)))


def revision_series(value: str | None) -> str | None:
    """Return 'P' or 'C' for ISO preliminary/construction revisions."""
    if not value:
        return None
    token = normalize_revision_token(value)
    if _PC_REVISION.fullmatch(token):
        return token[0]
    return None


def revision_rank(value: str | None) -> tuple:
    if not value:
        return (9, 0, "")
    rev = normalize_revision_token(value)
    match = re.fullmatch(r"P(\d{1,2})", rev)
    if match:
        return (0, int(match.group(1)), rev)
    match = re.fullmatch(r"C(\d{1,2})", rev)
    if match:
        return (1, int(match.group(1)), rev)
    match = re.fullmatch(r"([A-Z])(\d?)", rev)
    if match:
        return (2, ord(match.group(1)) * 10 + int(match.group(2) or 0), rev)
    match = re.fullmatch(r"(\d{1,2})", rev)
    if match:
        return (0, int(match.group(1)), rev)
    return (9, 0, rev)


def extract_suitability(text: str | None) -> str | None:
    """Return 'S2 - Suitable for Tender' or 'A - Construction' from code + description."""
    if not text:
        return None
    cleaned = fold_latin_lookalikes(text)
    cleaned = DATE_IN_TEXT.sub(" ", cleaned)
    cleaned = re.sub(r"\b[PC]\d{1,2}\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b[A-Z]\.[A-Z]\.?\b", " ", cleaned)
    tail = _SUITABILITY_TAIL.search(cleaned)
    if tail:
        cleaned = cleaned[: tail.start()]
    cleaned = re.sub(r"[\s\-–:/]+", " ", cleaned).strip(" -–:")
    if not cleaned:
        return None
    match = SUITABILITY_IN_TEXT.search(cleaned)
    if match:
        code = match.group(1).upper()
        remainder = f"{cleaned[: match.start()]} {cleaned[match.end() :]}"
    else:
        tokens = re.findall(r"[A-Za-z0-9&]+", cleaned)
        letters = [tok for tok in tokens if len(tok) == 1 and tok.isalpha()]
        words = [tok for tok in tokens if len(tok) > 1]
        if len(letters) != 1 or not words:
            return None
        code = letters[0].upper()
        remainder = " ".join(tok for tok in tokens if tok.upper() != code)
    remainder = re.sub(r"[\s\-–:/]+", " ", remainder).strip(" -–:")
    remainder = _TRAILING_INITIALS.sub("", remainder).strip(" -–:")
    if remainder:
        return f"{code} - {remainder}"
    return code


def _year(raw: str) -> int:
    year = int(raw)
    if year < 100:
        return 2000 + year if year < 80 else 1900 + year
    return year


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    match = re.fullmatch(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})", text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), _year(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            try:
                return date(year, day, month)
            except ValueError:
                return None
    match = re.fullmatch(r"(\d{1,2})\s*([A-Za-z]{3,9})\s*(\d{2,4})", text)
    if match:
        month = MONTHS.get(match.group(2)[:3].upper())
        if not month:
            return None
        try:
            return date(_year(match.group(3)), month, int(match.group(1)))
        except ValueError:
            return None
    match = DATE_IN_TEXT.search(text)
    if match and match.group(0) != text:
        return parse_date(match.group(0))
    try:
        return datetime.strptime(text, "%d %B %Y").date()
    except ValueError:
        return None


def dates_equal(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    a, b = parse_date(left), parse_date(right)
    if a and b:
        return a == b
    return re.sub(r"\s+", "", left).upper() == re.sub(r"\s+", "", right).upper()


def suitability_code(value: str | None) -> str | None:
    if not value:
        return None
    match = SUITABILITY_IN_TEXT.search(value)
    if match:
        return match.group(1).upper()
    match = re.match(r"^([A-Z])(?:\s|$|-)", value.strip())
    return match.group(1).upper() if match else None
