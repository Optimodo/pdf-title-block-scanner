from __future__ import annotations

from datetime import date

from drawing_qa.extract import all_text, find_label, line_text, normalize_label, words_to_lines
from drawing_qa.models import (
    HistoryRow,
    HistorySpec,
    RectFrac,
    RevisionHistory,
    TitleBlockLayout,
    Word,
    bbox_of,
)
from drawing_qa.tokens import (
    DATE_IN_TEXT,
    extract_suitability,
    is_pc_revision,
    is_revision_token,
    normalize_revision_token,
    parse_date,
    revision_rank,
    suitability_code,
)

HISTORY_HEADINGS = (
    "REVISION HISTORY",
    "REV HISTORY",
    "ISSUE HISTORY",
    "AMENDMENT HISTORY",
    "AMENDMENTS",
)


def history_search_region(layout: TitleBlockLayout) -> RectFrac:
    spec = layout.history or HistorySpec()
    if spec.region is not None:
        if spec.relative_to == "page":
            return spec.region.clamp()
        region = layout.region
        width = region.right - region.left
        height = region.bottom - region.top
        return RectFrac(
            left=region.left + spec.region.left * width,
            top=region.top + spec.region.top * height,
            right=region.left + spec.region.right * width,
            bottom=region.top + spec.region.bottom * height,
        ).clamp()
    region = layout.region
    return RectFrac(
        left=max(0.0, region.left - spec.expand_left),
        top=max(0.0, region.top - spec.expand_top),
        right=min(1.0, region.right + spec.expand_right),
        bottom=min(1.0, region.bottom + spec.expand_bottom),
    )


def _clip_words_to_history_table(
    words: list[Word],
) -> tuple[list[Word], list[Word] | None]:
    """Keep the amendments/revision table around its heading, if present."""
    heading_words = None
    for heading in HISTORY_HEADINGS:
        found = find_label(words, heading)
        if found:
            heading_words = found
            break
    if not heading_words:
        return words, None
    # Rows may sit above the caption (MBS) or just below it.
    top = min(word.y0 for word in heading_words) - 280
    bottom = max(word.y1 for word in heading_words) + 28
    clipped = [word for word in words if top <= word.cy <= bottom]
    return clipped or words, heading_words


def _line_revision(line: list[Word]) -> Word | None:
    candidates = [word for word in line if is_revision_token(word.text)]
    if not candidates:
        return None
    pc = [word for word in candidates if is_pc_revision(word.text)]
    return (pc or candidates)[0]


def _line_date(line: list[Word]) -> str | None:
    text = line_text(line)
    match = DATE_IN_TEXT.search(text)
    return match.group(0) if match else None


def _parse_row(line: list[Word]) -> HistoryRow | None:
    rev_word = _line_revision(line)
    date_value = _line_date(line)
    if rev_word is None or not date_value:
        return None
    suit = extract_suitability(line_text(line))
    skip = {id(rev_word)}
    description_words = []
    for word in line:
        if id(word) in skip:
            continue
        if DATE_IN_TEXT.search(word.text):
            continue
        if suitability_code(word.text) and len(word.text) <= 3:
            continue
        if normalize_label(word.text) in {"REV", "REVISION", "DATE", "STATUS", "SUITABILITY"}:
            continue
        description_words.append(word)
    description = " ".join(w.text for w in description_words).strip() or None
    if suit and description:
        code = suitability_code(suit)
        if code and description.upper().startswith(code):
            description = description[len(code) :].strip(" -–:") or None
    return HistoryRow(
        revision=normalize_revision_token(rev_word.text),
        date=date_value,
        suitability=suit,
        description=description,
        words=list(line),
    )


def _cluster_rows(rows: list[HistoryRow], x_tolerance: float = 24.0) -> list[list[HistoryRow]]:
    clusters: list[list[HistoryRow]] = []
    for row in rows:
        rev_word = _line_revision(row.words)
        if rev_word is None:
            continue
        placed = False
        for cluster in clusters:
            sample = _line_revision(cluster[0].words)
            if sample and abs(rev_word.x0 - sample.x0) <= x_tolerance:
                cluster.append(row)
                placed = True
                break
        if not placed:
            clusters.append([row])
    clusters.sort(key=len, reverse=True)
    return clusters


def _row_recency(row: HistoryRow) -> tuple:
    parsed = parse_date(row.date) if row.date else None
    return (parsed or date.min, revision_rank(row.revision))


def _row_first_issue(row: HistoryRow) -> tuple:
    # Original issue is the lowest revision rank (P01), even when the printed
    # date is not a valid calendar date (30.02.26).
    parsed = parse_date(row.date) if row.date else None
    return (revision_rank(row.revision), parsed or date.max)


def history_first_row(history: RevisionHistory) -> HistoryRow | None:
    """Oldest dated history row (original issue), else lowest revision rank."""
    if history.first:
        return history.first
    if not history.rows:
        return None
    return min(history.rows, key=_row_first_issue)


_HISTORY_CHROME = {
    "REV",
    "REVISION",
    "DATE",
    "DESCRIPTION",
    "BY",
    "AMENDMENTS",
    "PROJECT",
    "CLIENT",
    "STATUS",
    "SUITABILITY",
}


def _is_history_chrome(line: list[Word]) -> bool:
    label = normalize_label(line_text(line))
    if not label:
        return True
    tokens = label.split()
    if tokens[0] in _HISTORY_CHROME and not _line_revision(line):
        return True
    return label in _HISTORY_CHROME


def _description_left(row: HistoryRow) -> float | None:
    rev = _line_revision(row.words)
    date_words = [w for w in row.words if DATE_IN_TEXT.search(w.text)]
    skip = set()
    if rev is not None:
        skip.add(id(rev))
    skip.update(id(word) for word in date_words)
    desc = [word for word in row.words if id(word) not in skip]
    if desc:
        return min(word.x0 for word in desc)
    if date_words:
        return max(word.x1 for word in date_words) + 4
    if rev is not None:
        return rev.x1 + 4
    return None


def _is_wrapped_description(line: list[Word], prev: HistoryRow) -> bool:
    """True when this line is a wrapped description under the previous history row."""
    if _is_history_chrome(line) or _line_revision(line):
        return False
    prev_bottom = max(word.y1 for word in prev.words)
    line_top = min(word.y0 for word in line)
    if line_top < prev_bottom - 2 or line_top > prev_bottom + 22:
        return False
    desc_left = _description_left(prev)
    if desc_left is None:
        return False
    return abs(min(word.x0 for word in line) - desc_left) <= 48


def _parse_history_lines(lines: list[list[Word]]) -> list[HistoryRow]:
    """Parse rows and fold wrapped description lines into the previous row."""
    parsed: list[HistoryRow] = []
    for line in lines:
        row = _parse_row(line)
        if row:
            parsed.append(row)
            continue
        if not parsed or not _is_wrapped_description(line, parsed[-1]):
            continue
        extra = line_text(line).strip()
        if not extra:
            continue
        prev = parsed[-1]
        prev.description = f"{prev.description} {extra}".strip() if prev.description else extra
        prev.words.extend(line)
    return parsed


def detect_revision_history(words: list[Word], spec: HistorySpec | None = None) -> RevisionHistory:
    spec = spec or HistorySpec()
    result = RevisionHistory()
    words, heading_words = _clip_words_to_history_table(words)
    heading = bool(heading_words)
    if not heading:
        blob = f" {normalize_label(all_text(words))} "
        heading = any(f" {item} " in blob for item in HISTORY_HEADINGS)
    parsed = _parse_history_lines(words_to_lines(words))
    if not parsed:
        return result

    clusters = _cluster_rows(parsed)
    cluster = clusters[0] if clusters else []
    min_rows = 1 if heading else spec.min_rows
    if len(cluster) < min_rows:
        result.notes.append("No revision-history table detected")
        return result

    cluster.sort(key=lambda row: min(w.y0 for w in row.words))
    latest = max(cluster, key=_row_recency)
    boxes = [row.bbox for row in cluster if row.bbox]
    bbox = boxes[0]
    for extra in boxes[1:]:
        bbox = bbox.union(extra)
    # Include a header line just above the first data row when present.
    first_top = min(row.bbox.y0 for row in cluster if row.bbox)
    header_words = [
        word
        for word in words
        if first_top - 18 <= word.cy < first_top - 1
    ]
    if header_words:
        header_box = bbox_of(header_words)
        if header_box:
            bbox = bbox.union(header_box)

    result.rows = cluster
    result.latest = latest
    result.first = min(cluster, key=_row_first_issue)
    result.bbox = bbox
    if heading_words:
        heading_box = bbox_of(heading_words)
        if heading_box:
            result.bbox = bbox.union(heading_box)
    result.notes.append(
        f"Revision history: {len(cluster)} row(s); latest {latest.revision or '?'}"
    )
    older = [row.revision for row in cluster if row.revision != latest.revision]
    if older:
        result.notes.append("Older history revisions ignored: " + ", ".join(dict.fromkeys(older)))
    return result
