from __future__ import annotations

import re
from datetime import date, datetime

REV_TOKEN = re.compile(r"^(?:[PC]\d{2}|[A-Z]\d?)$", re.IGNORECASE)
SUITABILITY_TOKEN = re.compile(r"^(?:S[0-7]|A[1-3]|B[1-2])$", re.IGNORECASE)
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
    r"\b(S[0-7]|A[1-3]|B[1-2])\b(?:\s*[-–:]\s*[A-Za-z][A-Za-z0-9 &/]+)?",
    re.IGNORECASE,
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


def is_revision_token(text: str) -> bool:
    return bool(REV_TOKEN.fullmatch(text.strip()))


def revision_rank(value: str | None) -> tuple:
    if not value:
        return (9, 0, "")
    rev = value.strip().upper()
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
    if not text:
        return None
    match = SUITABILITY_IN_TEXT.search(text)
    if not match:
        return None
    code = match.group(1).upper()
    rest = text[match.end() :].strip(" -–:")
    if rest:
        return f"{code} {rest}".strip()
    full = match.group(0).strip()
    return re.sub(r"\s+", " ", full).upper() if full.upper().startswith(code) else code


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
    return match.group(1).upper() if match else None
