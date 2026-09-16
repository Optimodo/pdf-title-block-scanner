from __future__ import annotations

import re

from drawing_qa.extract import (
    all_text,
    apply_pattern,
    extract_near_label_words,
    extract_words,
    find_label,
    line_text,
    normalize_label,
    page_rect,
    words_outside,
    words_to_lines,
)
from drawing_qa.history import detect_revision_history, history_search_region
from drawing_qa.models import (
    ExtractedField,
    FieldSpec,
    RectFrac,
    TitleBlockFields,
    TitleBlockLayout,
    Word,
    bbox_of,
)
from drawing_qa.tokens import normalize_revision_token
from drawing_qa.models import (
    ExtractedField,
    FieldSpec,
    RectFrac,
    TitleBlockFields,
    TitleBlockLayout,
    Word,
    bbox_of,
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
        remaining_exclude = exclude
        for _ in range(5):
            found = extract_near_label_words(
                words,
                spec.labels,
                spec.direction,
                stop_labels=_all_labels(layout),
                exclude=remaining_exclude,
            )
            if not found:
                return ExtractedField(name=name)
            text, value_words = found
            extracted = apply_pattern(text, value_words, spec.pattern, name)
            if extracted.value:
                return extracted
            # Skip this label occurrence (not the whole below-window) and try the next.
            label_hit = None
            for label in spec.labels:
                label_hit = find_label(words, label, exclude=remaining_exclude)
                if label_hit:
                    break
            box = bbox_of(label_hit) if label_hit else bbox_of(value_words)
            if box is None:
                return ExtractedField(name=name)
            remaining_exclude = box if remaining_exclude is None else remaining_exclude.union(box)
        return ExtractedField(name=name)
    return ExtractedField(name=name)


def _layout_fits_page(page, layout: TitleBlockLayout) -> bool:
    wanted = (layout.orientation or "").strip().lower()
    if wanted not in {"portrait", "landscape"}:
        return True
    portrait = float(page.rect.height) > float(page.rect.width)
    return wanted == "portrait" if portrait else wanted == "landscape"


def extract_titleblock(
    page,
    layouts: list[TitleBlockLayout],
    min_score: float,
) -> TitleBlockFields:
    usable = [layout for layout in layouts if _layout_fits_page(page, layout)]
    candidates: list[tuple[float, TitleBlockLayout]] = []
    for layout in usable:
        words = extract_words(page, layout.region)
        score = score_layout(words, layout)
        threshold = max(min_score, layout.min_score)
        if score >= threshold:
            candidates.append((score, layout))
    candidates.sort(key=lambda item: item[0], reverse=True)

    if not candidates:
        best: tuple[float, TitleBlockLayout] | None = None
        for layout in usable:
            words = extract_words(page, layout.region)
            score = score_layout(words, layout)
            if best is None or score > best[0]:
                best = (score, layout)
        if best is None:
            return TitleBlockFields(notes=["No layouts configured"])
        score, layout = best
        result = TitleBlockFields(
            layout_id=layout.id,
            layout_name=layout.name,
            score=round(score, 3),
        )
        threshold = max(min_score, layout.min_score)
        result.notes.append(
            f"Best layout '{layout.id}' scored {score:.2f}, below threshold {threshold:.2f}"
        )
        return result

    filled: list[TitleBlockFields] = []
    for score, layout in candidates:
        filled.append(_extract_layout_fields(page, layout, score))
    return _choose_layout_result(filled, layouts)


def _choose_layout_result(
    filled: list[TitleBlockFields],
    layouts: list[TitleBlockLayout],
) -> TitleBlockFields:
    """Prefer a layout that read a doc-ref, then the most complete title/fields."""
    by_id = {layout.id: layout for layout in layouts}

    def sort_key(item: TitleBlockFields) -> tuple:
        layout = by_id.get(item.layout_id)
        min_score = layout.min_score if layout else 0.0
        filled_count = sum(
            1
            for name in ("document_reference", "title", "revision", "suitability", "date")
            if getattr(item, name)
        )
        return (
            1 if item.document_reference else 0,
            filled_count,
            len(item.title or ""),
            item.score,
            min_score,
        )

    return max(filled, key=sort_key)


def _extract_layout_fields(page, layout: TitleBlockLayout, score: float) -> TitleBlockFields:
    result = TitleBlockFields(
        layout_id=layout.id,
        layout_name=layout.name,
        score=round(score, 3),
    )

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
    result.client = (extracted.get("client") or ExtractedField("client")).value
    if result.history.rows and result.revision:
        current = normalize_revision_token(result.revision)
        for row in result.history.rows:
            if row.revision and normalize_revision_token(row.revision) == current:
                result.history.latest = row
                break
    missing = [name for name in ("document_reference", "revision") if not getattr(result, name)]
    if missing:
        result.notes.append("Missing title-block fields: " + ", ".join(missing))
    empty_optional = [name for name in ("suitability", "date") if not getattr(result, name)]
    if empty_optional:
        result.notes.append("Optional fields not found: " + ", ".join(empty_optional))
    return result


_TITLE_STOP_HEADINGS = {
    "SUITABILITY",
    "STATUS",
    "PURPOSE OF ISSUE",
    "DESIGNED BY",
    "DRAWN BY",
    "CHECKED BY",
    "NUMBER",
    "REVISION",
    "DATE",
    "SCALE",
    "SCALES",
    "PROJECT NUMBER",
    "CLIENT",
    "CLIENT CONTACT",
    "CLIENT NAME",
}


def recover_unlabelled_fields(
    page,
    layouts: list[TitleBlockLayout],
    titleblock: TitleBlockFields,
    *,
    allowed_clients: list[str] | None = None,
) -> TitleBlockFields:
    """Fill client/title when the value is printed but the heading word is missing."""
    layout = next((item for item in layouts if item.id == titleblock.layout_id), None)
    if layout is None:
        return titleblock
    words = extract_words(page, layout.region)
    if titleblock.history and titleblock.history.bbox:
        words = words_outside(words, titleblock.history.bbox)
    if not titleblock.client and allowed_clients:
        found = _client_from_whitelist(words, allowed_clients)
        if found:
            titleblock.client = found
            titleblock.fields["client"] = ExtractedField(
                name="client", value=found, source="whitelist"
            )
            titleblock.notes.append(
                "Client name taken from title-block text (no CLIENT heading)"
            )
    if not titleblock.title:
        found = _title_below_project(words, allowed_clients)
        if found:
            titleblock.title = found
            titleblock.fields["title"] = ExtractedField(
                name="title", value=found, source="unlabelled"
            )
            titleblock.notes.append(
                "Title taken from the title-block cell (no TITLE heading)"
            )
    return titleblock


def _client_from_whitelist(words: list[Word], allowed: list[str]) -> str | None:
    from drawing_qa.client import client_is_allowed, normalize_client

    needles = sorted(
        ((normalize_client(name), name) for name in allowed if normalize_client(name)),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    if not needles:
        return None
    for line in words_to_lines(words):
        text = line_text(line)
        if client_is_allowed(text, allowed):
            return text
    blob = all_text(words)
    hay = f" {normalize_client(blob)} "
    for needle, name in needles:
        if f" {needle} " in hay:
            return name
    return None


def _title_below_project(
    words: list[Word],
    allowed_clients: list[str] | None,
) -> str | None:
    from drawing_qa.client import client_is_allowed

    project = find_label(words, "PROJECT")
    if not project:
        return None
    y_after = max(word.y1 for word in project)
    collected: list[str] = []
    skipped_project_name = False
    for line in words_to_lines(words):
        if min(word.y0 for word in line) < y_after - 2:
            continue
        text = line_text(line)
        heading = normalize_label(text)
        if heading in {"TITLE", "DRAWING TITLE", "PROJECT"}:
            continue
        if not skipped_project_name:
            skipped_project_name = True
            continue
        if heading in _TITLE_STOP_HEADINGS or any(
            heading.startswith(stop + " ") for stop in _TITLE_STOP_HEADINGS
        ):
            break
        if allowed_clients and client_is_allowed(text, allowed_clients):
            break
        if text:
            collected.append(text)
        if len(collected) >= 4:
            break
    joined = " ".join(collected).strip()
    return joined or None


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
