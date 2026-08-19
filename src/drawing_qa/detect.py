from __future__ import annotations

import re

from drawing_qa.extract import (
    all_text,
    apply_pattern,
    extract_near_label_words,
    extract_words,
    page_rect,
    words_outside,
)
from drawing_qa.history import detect_revision_history, history_search_region
from drawing_qa.models import (
    ExtractedField,
    FieldSpec,
    RectFrac,
    TitleBlockFields,
    TitleBlockLayout,
    Word,
)


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


def _all_labels(layout: TitleBlockLayout) -> list[str]:
    labels: list[str] = []
    for spec in layout.fields.values():
        labels.extend(spec.labels)
    labels.extend(layout.anchors)
    return list(dict.fromkeys(labels))


def extract_field(
    page,
    layout: TitleBlockLayout,
    spec: FieldSpec,
    name: str,
    exclude=None,
) -> ExtractedField:
    words = extract_words(page, layout.region)
    if exclude is not None:
        words = words_outside(words, exclude)
    if spec.clip is not None:
        field_region = _clip_to_page(layout.region, spec.clip, spec.relative_to)
        clip_words = extract_words(page, field_region)
        if exclude is not None:
            clip_words = words_outside(clip_words, exclude)
        text = all_text(clip_words).replace("\n", " ")
        return apply_pattern(text, clip_words, spec.pattern, name)
    if spec.labels:
        found = extract_near_label_words(
            words,
            spec.labels,
            spec.direction,
            stop_labels=_all_labels(layout),
            exclude=exclude,
        )
        if not found:
            return ExtractedField(name=name)
        text, value_words = found
        return apply_pattern(text, value_words, spec.pattern, name)
    return ExtractedField(name=name)


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

    history_words = extract_words(page, history_search_region(layout))
    result.history = detect_revision_history(history_words, layout.history)
    result.notes.extend(result.history.notes)
    exclude = result.history.bbox

    extracted: dict[str, ExtractedField] = {}
    for name, spec in layout.fields.items():
        extracted[name] = extract_field(page, layout, spec, name, exclude=exclude)

    latest = result.history.latest
    if latest:
        if not extracted.get("revision") or not extracted["revision"].value:
            if latest.revision:
                extracted["revision"] = ExtractedField(
                    name="revision",
                    value=latest.revision,
                    words=latest.words,
                    source="history",
                )
                result.notes.append("Current revision taken from latest history row")
        if (not extracted.get("date") or not extracted["date"].value) and latest.date:
            extracted["date"] = ExtractedField(
                name="date",
                value=latest.date,
                words=latest.words,
                source="history",
            )
            result.notes.append("Current date taken from latest history row")
        if (not extracted.get("suitability") or not extracted["suitability"].value) and latest.suitability:
            extracted["suitability"] = ExtractedField(
                name="suitability",
                value=latest.suitability,
                words=latest.words,
                source="history",
            )
            result.notes.append("Current suitability taken from latest history row")

    result.fields = extracted
    result.document_reference = (extracted.get("document_reference") or ExtractedField("document_reference")).value
    result.title = (extracted.get("title") or ExtractedField("title")).value
    result.revision = (extracted.get("revision") or ExtractedField("revision")).value
    result.suitability = (extracted.get("suitability") or ExtractedField("suitability")).value
    result.date = (extracted.get("date") or ExtractedField("date")).value
    missing = [name for name in ("document_reference", "revision") if not getattr(result, name)]
    if missing:
        result.notes.append("Missing title-block fields: " + ", ".join(missing))
    empty_optional = [name for name in ("suitability", "date") if not getattr(result, name)]
    if empty_optional:
        result.notes.append("Optional fields not found: " + ", ".join(empty_optional))
    return result


def region_debug_text(page, region: RectFrac) -> str:
    words = extract_words(page, region)
    lines = []
    for word in words:
        lines.append(f"{word.x0:7.1f},{word.y0:7.1f}  {word.text}")
    return "\n".join(lines)


def crop_region_pixmap(page, region: RectFrac, zoom: float = 2.0):
    import pymupdf

    clip = page_rect(page, region)
    matrix = pymupdf.Matrix(zoom, zoom)
    return page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
