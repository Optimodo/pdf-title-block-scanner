from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from drawing_qa.checks import CheckOptions
from drawing_qa.document_list import DocumentListLayout, load_document_list_layout
from drawing_qa.models import FieldSpec, HistorySpec, RectFrac, TitleBlockLayout
from drawing_qa.paths import bundled_config_dir, resolve_config_dir
from drawing_qa.suitability import DEFAULT_PURPOSE_CONSTRUCTION, DEFAULT_PURPOSE_REVIEW
from drawing_qa.timing import configure as configure_timing


@dataclass
class SpellCheckConfig:
    enabled: bool = True
    language: str = "en_GB"
    check_title: bool = True
    fail_on_error: bool = True


@dataclass
class ClientCheckConfig:
    enabled: bool = True
    fail_on_error: bool = True
    projects: dict[str, list[str]] = field(default_factory=dict)
    project_names: dict[str, str] = field(default_factory=dict)


@dataclass
class SuitabilityCheckConfig:
    enabled: bool = True
    fail_on_error: bool = True
    accept_code_only: bool = True
    values: list[str] = field(default_factory=list)
    purpose_enabled: bool = True
    purpose_review: list[str] = field(default_factory=lambda: list(DEFAULT_PURPOSE_REVIEW))
    purpose_construction: list[str] = field(
        default_factory=lambda: list(DEFAULT_PURPOSE_CONSTRUCTION)
    )
    projects: dict[str, list[str]] = field(default_factory=dict)
    project_names: dict[str, str] = field(default_factory=dict)
    suggested: list[str] = field(default_factory=list)


@dataclass
class PreviewConfig:
    all_files: bool = False


@dataclass
class DocumentListConfig:
    enabled: bool = True
    layout: DocumentListLayout | None = None


@dataclass
class AppConfig:
    field_count: int
    revision_pattern: str
    min_layout_score: float
    first_page_only: bool
    compare_rules: dict[str, str]
    layouts: list[TitleBlockLayout]
    spell_check: SpellCheckConfig | None = None
    suitability_check: SuitabilityCheckConfig | None = None
    client_check: ClientCheckConfig | None = None
    preview: PreviewConfig | None = None
    document_list: DocumentListConfig | None = None
    check_options: CheckOptions = field(default_factory=CheckOptions)


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
        orientation=str(data.get("orientation") or "").strip().lower(),
    )


def _project_suitability_lists(raw: dict) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Map ISO project codes (R459) to optional purpose-of-issue lists and names."""
    block = raw.get("projects") or {}
    if not isinstance(block, dict):
        return {}, {}
    projects: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for key, spec in block.items():
        code = str(key).strip().upper()
        if not code:
            continue
        name = ""
        if isinstance(spec, dict):
            items = spec.get("values") or []
            name = str(spec.get("name") or "").strip()
        elif isinstance(spec, list):
            items = spec
        else:
            continue
        values = [str(item).strip() for item in items if str(item).strip()]
        if values:
            projects[code] = values
            if name:
                names[code] = name
    return projects, names


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

    # Load spell check configuration
    spell_check_cfg = settings.get("spell_check") or {}
    spell_check = SpellCheckConfig(
        enabled=bool(spell_check_cfg.get("enabled", True)),
        language=str(spell_check_cfg.get("language", "en_GB")),
        check_title=bool(spell_check_cfg.get("check_title", True)),
        fail_on_error=bool(spell_check_cfg.get("fail_on_error", True)),
    )

    suitability_path = config_dir / "suitability.yaml"
    if not suitability_path.is_file():
        bundled = bundled_config_dir() / "suitability.yaml"
        if bundled.is_file():
            suitability_path = bundled
    suitability_raw = {}
    if suitability_path.is_file():
        suitability_raw = yaml.safe_load(suitability_path.read_text(encoding="utf-8")) or {}
    values = [str(item).strip() for item in (suitability_raw.get("values") or []) if str(item).strip()]
    projects, project_names = _project_suitability_lists(suitability_raw)
    suggested = [
        str(item).strip()
        for item in (suitability_raw.get("suggested") or [])
        if str(item).strip()
    ]
    if not suggested:
        suggested = list(projects.get("R459") or [])
    if "purpose" in suitability_raw:
        purpose_raw = suitability_raw.get("purpose") or {}
        purpose_enabled = bool(purpose_raw.get("enabled", True))
        purpose_review = [
            str(item).strip()
            for item in (purpose_raw.get("review") or [])
            if str(item).strip()
        ]
        purpose_construction = [
            str(item).strip()
            for item in (purpose_raw.get("construction") or [])
            if str(item).strip()
        ]
    else:
        purpose_enabled = True
        purpose_review = list(DEFAULT_PURPOSE_REVIEW)
        purpose_construction = list(DEFAULT_PURPOSE_CONSTRUCTION)
    suitability_check = SuitabilityCheckConfig(
        enabled=bool(suitability_raw.get("enabled", True)),
        fail_on_error=bool(suitability_raw.get("fail_on_error", True)),
        accept_code_only=bool(suitability_raw.get("accept_code_only", True)),
        values=values,
        purpose_enabled=purpose_enabled,
        purpose_review=purpose_review,
        purpose_construction=purpose_construction,
        projects=projects,
        project_names=project_names,
        suggested=suggested,
    )

    clients_path = config_dir / "clients.yaml"
    if not clients_path.is_file():
        bundled_clients = bundled_config_dir() / "clients.yaml"
        if bundled_clients.is_file():
            clients_path = bundled_clients
    clients_raw: dict = {}
    if clients_path.is_file():
        clients_raw = yaml.safe_load(clients_path.read_text(encoding="utf-8")) or {}
    client_projects, client_names = _project_suitability_lists(clients_raw)
    client_check = ClientCheckConfig(
        enabled=bool(clients_raw.get("enabled", True)),
        fail_on_error=bool(clients_raw.get("fail_on_error", True)),
        projects=client_projects,
        project_names=client_names,
    )

    timing_cfg = settings.get("timing") or {}
    configure_timing(bool(timing_cfg.get("enabled", False)))

    preview_cfg = settings.get("preview") or {}
    preview = PreviewConfig(
        all_files=bool(preview_cfg.get("all_files", False)),
    )

    lists_path = config_dir / "document_lists.yaml"
    if not lists_path.is_file():
        bundled_lists = bundled_config_dir() / "document_lists.yaml"
        if bundled_lists.is_file():
            lists_path = bundled_lists
    lists_raw = {}
    if lists_path.is_file():
        lists_raw = yaml.safe_load(lists_path.read_text(encoding="utf-8")) or {}
    document_list = DocumentListConfig(
        enabled=bool(lists_raw.get("enabled", True)),
        layout=load_document_list_layout(lists_raw),
    )

    return AppConfig(
        field_count=int(filename_cfg.get("field_count", 7)),
        revision_pattern=str(
            filename_cfg.get("revision_pattern", r"(?:[PC]\d{2}|[A-Z]\d?)")
        ),
        min_layout_score=float(extraction_cfg.get("min_layout_score", 0.7)),
        first_page_only=bool(extraction_cfg.get("first_page_only", True)),
        compare_rules={str(k): str(v) for k, v in rules.items()},
        layouts=layouts,
        spell_check=spell_check,
        suitability_check=suitability_check,
        client_check=client_check,
        preview=preview,
        document_list=document_list,
    )


def compile_revision_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)
