from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from drawing_qa.models import FieldSpec, HistorySpec, RectFrac, TitleBlockLayout
from drawing_qa.paths import resolve_config_dir


@dataclass
class AppConfig:
    field_count: int
    revision_pattern: str
    min_layout_score: float
    first_page_only: bool
    compare_rules: dict[str, str]
    layouts: list[TitleBlockLayout]


def _rect(data: dict) -> RectFrac:
    return RectFrac(
        left=float(data["left"]),
        top=float(data["top"]),
        right=float(data["right"]),
        bottom=float(data["bottom"]),
    ).clamp()


def _field_spec(data: dict | None) -> FieldSpec:
    data = data or {}
    clip = _rect(data["clip"]) if data.get("clip") else None
    labels = data.get("labels") or []
    if isinstance(labels, str):
        labels = [labels]
    return FieldSpec(
        labels=[str(x) for x in labels],
        direction=str(data.get("direction", "auto")),
        pattern=data.get("pattern"),
        clip=clip,
        relative_to=str(data.get("relative_to", "region")),
    )


def _history_spec(data: dict | None) -> HistorySpec:
    data = data or {}
    region = _rect(data["region"]) if data.get("region") else None
    return HistorySpec(
        expand_left=float(data.get("expand_left", 0.25)),
        expand_right=float(data.get("expand_right", 0.0)),
        expand_top=float(data.get("expand_top", 0.05)),
        expand_bottom=float(data.get("expand_bottom", 0.0)),
        region=region,
        relative_to=str(data.get("relative_to", "page")),
        min_rows=int(data.get("min_rows", 2)),
    )


def load_layout(path: Path) -> TitleBlockLayout:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    fields_raw = data.get("fields") or {}
    fields = {name: _field_spec(spec) for name, spec in fields_raw.items()}
    groups = data.get("required_anchor_groups") or []
    groups = [[str(item) for item in group] for group in groups]
    anchors = [str(a) for a in (data.get("anchors") or [])]
    return TitleBlockLayout(
        id=str(data.get("id") or path.stem),
        name=str(data.get("name") or path.stem),
        region=_rect(data["region"]),
        anchors=anchors,
        required_anchor_groups=groups,
        fields=fields,
        min_score=float(data.get("min_score", 0.7)),
        history=_history_spec(data.get("history")),
    )


def load_config(config_dir: Path | None = None) -> AppConfig:
    if config_dir is None:
        config_dir = resolve_config_dir()
    settings_path = config_dir / "settings.yaml"
    if not settings_path.exists():
        raise FileNotFoundError(f"Missing settings file: {settings_path}")
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    filename_cfg = settings.get("filename") or {}
    extraction_cfg = settings.get("extraction") or {}
    compare_cfg = settings.get("compare") or {}
    rules = compare_cfg.get("fields") or {
        "document_reference": "required",
        "revision": "required",
        "title": "if_both_present",
        "suitability": "if_both_present",
        "date": "if_both_present",
    }

    layouts_dir = config_dir / "title_blocks"
    layouts: list[TitleBlockLayout] = []
    if layouts_dir.is_dir():
        for yaml_path in sorted(layouts_dir.glob("*.yaml")):
            layouts.append(load_layout(yaml_path))
        for yml_path in sorted(layouts_dir.glob("*.yml")):
            layouts.append(load_layout(yml_path))
    if not layouts:
        raise FileNotFoundError(f"No title-block layouts found in {layouts_dir}")

    return AppConfig(
        field_count=int(filename_cfg.get("field_count", 7)),
        revision_pattern=str(filename_cfg.get("revision_pattern", r"(?:[PC]\d{2}|[A-Z]\d?)")),
        min_layout_score=float(extraction_cfg.get("min_layout_score", 0.7)),
        first_page_only=bool(extraction_cfg.get("first_page_only", True)),
        compare_rules={str(k): str(v) for k, v in rules.items()},
        layouts=layouts,
    )


def compile_revision_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)
