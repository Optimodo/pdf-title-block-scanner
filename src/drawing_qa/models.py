from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class CheckStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    INCOMPLETE = "INCOMPLETE"
    UNDETECTED = "UNDETECTED"
    FILENAME_PARSE_ERROR = "FILENAME_PARSE_ERROR"
    ERROR = "ERROR"


@dataclass(frozen=True)
class RectFrac:
    """Axis-aligned rectangle as fractions of page width/height (origin top-left)."""

    left: float
    top: float
    right: float
    bottom: float

    def clamp(self) -> RectFrac:
        return RectFrac(
            left=max(0.0, min(self.left, 1.0)),
            top=max(0.0, min(self.top, 1.0)),
            right=max(0.0, min(self.right, 1.0)),
            bottom=max(0.0, min(self.bottom, 1.0)),
        )


@dataclass(frozen=True)
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class FieldSpec:
    labels: list[str] = field(default_factory=list)
    direction: str = "auto"
    pattern: str | None = None
    clip: RectFrac | None = None
    relative_to: str = "region"


@dataclass
class TitleBlockLayout:
    id: str
    name: str
    region: RectFrac
    anchors: list[str]
    required_anchor_groups: list[list[str]]
    fields: dict[str, FieldSpec]
    min_score: float = 0.7


@dataclass
class FilenameFields:
    raw_stem: str
    document_reference: str | None = None
    title: str | None = None
    revision: str | None = None
    parts: dict[str, str] = field(default_factory=dict)
    parse_ok: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class TitleBlockFields:
    layout_id: str | None = None
    layout_name: str | None = None
    score: float = 0.0
    document_reference: str | None = None
    title: str | None = None
    revision: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class FieldComparison:
    name: str
    filename_value: str | None
    titleblock_value: str | None
    matched: bool | None
    detail: str


@dataclass
class DocumentResult:
    path: Path
    filename: FilenameFields
    titleblock: TitleBlockFields
    comparisons: list[FieldComparison] = field(default_factory=list)
    status: CheckStatus = CheckStatus.ERROR
    notes: list[str] = field(default_factory=list)
    page_count: int = 0
    error: str | None = None
