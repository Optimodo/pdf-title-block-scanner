from __future__ import annotations

import re

from drawing_qa.models import BBox, ExtractedField, Word, bbox_of
from drawing_qa.tokens import DATE_IN_TEXT, extract_suitability, is_revision_token

try:
    import pymupdf
except ImportError:  # pragma: no cover
    pymupdf = None


def require_pymupdf() -> None:
    if pymupdf is None:
        raise RuntimeError("PyMuPDF is required. Install with: pip install pymupdf")


def page_rect(page, region):
    require_pymupdf()
    width = float(page.rect.width)
    height = float(page.rect.height)
    return pymupdf.Rect(
        region.left * width,
        region.top * height,
        region.right * width,
        region.bottom * height,
    )


def extract_words(page, region=None) -> list[Word]:
    require_pymupdf()
    clip = page_rect(page, region) if region else page.rect
    raw = page.get_text("words", clip=clip) or []
    words: list[Word] = []
    for item in raw:
        text = str(item[4]).strip()
        if not text:
            continue
        words.append(
            Word(
                x0=float(item[0]),
                y0=float(item[1]),
                x1=float(item[2]),
                y1=float(item[3]),
                text=text,
            )
        )
    words.sort(key=lambda w: (round(w.y0, 1), w.x0))
    return words


def words_to_lines(words: list[Word], y_tolerance: float = 4.0) -> list[list[Word]]:
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (w.cy, w.x0))
    lines: list[list[Word]] = []
    current: list[Word] = [ordered[0]]
    current_y = ordered[0].cy
    for word in ordered[1:]:
        if abs(word.cy - current_y) <= y_tolerance:
            current.append(word)
        else:
            current.sort(key=lambda w: w.x0)
            lines.append(current)
            current = [word]
            current_y = word.cy
    current.sort(key=lambda w: w.x0)
    lines.append(current)
    return lines


def line_text(line: list[Word]) -> str:
    return " ".join(word.text for word in line).strip()


def all_text(words: list[Word]) -> str:
    return "\n".join(line_text(line) for line in words_to_lines(words)).strip()


def normalize_label(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def words_outside(words: list[Word], bbox: BBox | None, pad: float = 2.0) -> list[Word]:
    if bbox is None:
        return list(words)
    box = bbox.inflate(pad)
    return [word for word in words if not box.contains_point(word.cx, word.cy)]


def find_label(
    words: list[Word],
    label: str,
    exclude: BBox | None = None,
) -> list[Word] | None:
    """Return the consecutive words that form a label, if present."""
    target = normalize_label(label).split()
    if not target:
        return None
    lines = words_to_lines(words)
    for line in lines:
        normalized = [normalize_label(w.text) for w in line]
        n = len(normalized)
        t = len(target)
        for i in range(n - t + 1):
            if normalized[i : i + t] != target:
                continue
            found = line[i : i + t]
            if exclude and all(exclude.contains_point(w.cx, w.cy) for w in found):
                continue
            return found
    return None


def _same_line_right(words: list[Word], label_words: list[Word]) -> list[Word]:
    right_edge = max(w.x1 for w in label_words)
    y0 = min(w.y0 for w in label_words)
    y1 = max(w.y1 for w in label_words)
    band_mid = (y0 + y1) / 2
    height = max(y1 - y0, 1.0)
    chosen: list[Word] = []
    for word in words:
        if word in label_words:
            continue
        if word.x0 < right_edge - 1:
            continue
        if abs(word.cy - band_mid) <= height * 0.8:
            chosen.append(word)
    chosen.sort(key=lambda w: w.x0)
    return chosen


def height_of(words: list[Word]) -> float:
    return max(max(w.y1 for w in words) - min(w.y0 for w in words), 8.0)


def _below(words: list[Word], label_words: list[Word]) -> list[Word]:
    x0 = min(w.x0 for w in label_words)
    x1 = max(w.x1 for w in label_words)
    y1 = max(w.y1 for w in label_words)
    width = max(x1 - x0, 1.0)
    band_left = x0 - width * 0.25
    band_right = x1 + width * 2.5
    chosen: list[Word] = []
    for word in words:
        if word in label_words:
            continue
        if word.y0 < y1 - 1:
            continue
        if word.x1 < band_left or word.x0 > band_right:
            continue
        if word.y0 > y1 + height_of(label_words) * 6:
            continue
        chosen.append(word)
    if not chosen:
        return []
    return words_to_lines(chosen)[0]


def _label_token_length(words: list[Word], labels: list[str]) -> int:
    if not words or not labels:
        return 0
    normalized = [normalize_label(w.text) for w in words]
    for label in labels:
        target = normalize_label(label).split()
        if target and normalized[: len(target)] == target:
            return len(target)
    return 0


def take_until_label(words: list[Word], stop_labels: list[str]) -> list[Word]:
    """Keep value words until another title-block heading begins."""
    kept: list[Word] = []
    i = 0
    while i < len(words):
        skip = _label_token_length(words[i:], stop_labels)
        if skip:
            break
        kept.append(words[i])
        i += 1
    return kept


def extract_near_label_words(
    words: list[Word],
    labels: list[str],
    direction: str = "auto",
    stop_labels: list[str] | None = None,
    exclude: BBox | None = None,
) -> tuple[str, list[Word]] | None:
    search_words = words_outside(words, exclude)
    label_words = None
    used_label = None
    for label in labels:
        found = find_label(search_words, label, exclude=exclude)
        if found:
            label_words = found
            used_label = label
            break
    if not label_words:
        return None

    stops = [
        item
        for item in (stop_labels or [])
        if normalize_label(item) != normalize_label(used_label or "")
    ]
    directions = [direction] if direction != "auto" else ["right", "below"]
    for d in directions:
        if d == "right":
            value_words = _same_line_right(search_words, label_words)
        elif d == "below":
            value_words = _below(search_words, label_words)
        else:
            raise ValueError(f"Unknown direction {d} for label {used_label}")
        value_words = take_until_label(value_words, stops)
        text = " ".join(w.text for w in value_words).strip()
        if text:
            return text, value_words
    return None


def extract_near_label(
    words: list[Word],
    labels: list[str],
    direction: str = "auto",
    stop_labels: list[str] | None = None,
    exclude: BBox | None = None,
) -> str | None:
    found = extract_near_label_words(words, labels, direction, stop_labels, exclude)
    return found[0] if found else None


def apply_pattern(text: str | None, words: list[Word], pattern: str | None, field_name: str) -> ExtractedField:
    if not text:
        return ExtractedField(name=field_name)
    if field_name == "suitability":
        value = extract_suitability(text) or (text.strip() or None)
        return ExtractedField(name=field_name, value=value, words=words)
    if field_name == "date":
        match = DATE_IN_TEXT.search(text)
        value = match.group(0) if match else text.strip()
        kept = [w for w in words if DATE_IN_TEXT.search(w.text) or w.text in (value or "")]
        return ExtractedField(name=field_name, value=value, words=kept or words)
    if field_name == "revision":
        token = next((w for w in words if is_revision_token(w.text)), None)
        if token:
            return ExtractedField(name=field_name, value=token.text.upper(), words=[token])
    if not pattern:
        return ExtractedField(name=field_name, value=text.strip() or None, words=words)
    match = re.search(pattern, text, flags=re.IGNORECASE)
    value = match.group(0).strip() if match else text.strip()
    return ExtractedField(name=field_name, value=value or None, words=words)
