from __future__ import annotations

import re

from drawing_qa.extract import all_text, extract_near_label, extract_words, page_rect
from drawing_qa.models import FieldSpec, RectFrac, TitleBlockFields, TitleBlockLayout, Word


def _normalize_for_search(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _contains_anchor(haystack: str, anchor: str) -> bool:
    hay = f" {_normalize_for_search(haystack)} "
    needle = f" {_normalize_for_search(anchor)} "
    return needle in hay if needle.strip() else False


def score_layout(words: list[Word], layout: TitleBlockLayout) -> float:
    blob = all_text(words)
    if not blob:
        return 0.0

    groups = layout.required_anchor_groups
    if groups:
        hits = 0
        for group in groups:
            if any(_contains_anchor(blob, item) for item in group):
                hits += 1
        return hits / len(groups)

    anchors = layout.anchors
    if not anchors:
        return 0.0
    hits = sum(1 for anchor in anchors if _contains_anchor(blob, anchor))
    return hits / len(anchors)


def _clip_to_page(region: RectFrac, clip: RectFrac, relative_to: str) -> RectFrac:
    if relative_to == "page":
        return clip
    width = region.right - region.left
    height = region.bottom - region.top
    return RectFrac(
        left=region.left + clip.left * width,
        top=region.top + clip.top * height,
        right=region.left + clip.right * width,
        bottom=region.top + clip.bottom * height,
    )


def _apply_pattern(value: str | None, pattern: str | None) -> str | None:
    if value is None:
        return None
    if not pattern:
        return value.strip() or None
    match = re.search(pattern, value, flags=re.IGNORECASE)
    return match.group(0).strip() if match else value.strip() or None


def _all_labels(layout: TitleBlockLayout) -> list[str]:
    labels: list[str] = []
    for spec in layout.fields.values():
        labels.extend(spec.labels)
    labels.extend(layout.anchors)
    # Preserve order while dropping duplicates.
    return list(dict.fromkeys(labels))


def extract_field(page, layout: TitleBlockLayout, spec: FieldSpec) -> str | None:
    words = extract_words(page, layout.region)
    if spec.clip is not None:
        field_region = _clip_to_page(layout.region, spec.clip, spec.relative_to)
        clip_words = extract_words(page, field_region)
        return _apply_pattern(all_text(clip_words).replace("\n", " "), spec.pattern)
    if spec.labels:
        value = extract_near_label(
            words,
            spec.labels,
            spec.direction,
            stop_labels=_all_labels(layout),
        )
        return _apply_pattern(value, spec.pattern)
    return None


def extract_titleblock(
    page,
    layouts: list[TitleBlockLayout],
    min_score: float,
) -> TitleBlockFields:
    best: tuple[float, TitleBlockLayout, list[Word]] | None = None
    for layout in layouts:
        words = extract_words(page, layout.region)
        score = score_layout(words, layout)
        if best is None or score > best[0]:
            best = (score, layout, words)

    if best is None:
        return TitleBlockFields(notes=["No layouts configured"])

    score, layout, _words = best
    result = TitleBlockFields(
        layout_id=layout.id,
        layout_name=layout.name,
        score=round(score, 3),
    )
    threshold = max(min_score, layout.min_score)
    if score < threshold:
        result.notes.append(
            f"Best layout '{layout.id}' scored {score:.2f}, below threshold {threshold:.2f}"
        )
        return result

    fields = {}
    for name, spec in layout.fields.items():
        fields[name] = extract_field(page, layout, spec)

    result.document_reference = fields.get("document_reference")
    result.title = fields.get("title")
    result.revision = fields.get("revision")
    missing = [
        name
        for name in ("document_reference", "revision")
        if not fields.get(name)
    ]
    if missing:
        result.notes.append("Missing title-block fields: " + ", ".join(missing))
    return result


def region_debug_text(page, region: RectFrac) -> str:
    words = extract_words(page, region)
    lines = []
    for word in words:
        lines.append(
            f"{word.x0:7.1f},{word.y0:7.1f}  {word.text}"
        )
    return "\n".join(lines)


def crop_region_pixmap(page, region: RectFrac, zoom: float = 2.0):
    import pymupdf

    clip = page_rect(page, region)
    matrix = pymupdf.Matrix(zoom, zoom)
    return page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
