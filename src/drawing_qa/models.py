from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class CheckStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    HISTORY_MISMATCH = "HISTORY_MISMATCH"
    INCOMPLETE = "INCOMPLETE"
    UNDETECTED = "UNDETECTED"
    SPELLING_ERROR = "SPELLING_ERROR"
    DUPLICATE_REFERENCE = "DUPLICATE_REFERENCE"
    DATE_REGRESSION = "DATE_REGRESSION"
    SUITABILITY_ERROR = "SUITABILITY_ERROR"
    FILENAME_PARSE_ERROR = "FILENAME_PARSE_ERROR"
    ERROR = "ERROR"
    MULTIPLE_ISSUES = "MULTIPLE_ISSUES"


class Confidence(StrEnum):
    HIGH = "HIGH"
    REVIEW = "REVIEW"


MAIN_FIELDS = (
    "document_reference",
    "title",
    "revision",
    "suitability",
    "date",
)


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
class BBox:
    """Axis-aligned rectangle in PDF page coordinates (origin top-left)."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(self.x1 - self.x0, 1.0)

    @property
    def height(self) -> float:
        return max(self.y1 - self.y0, 1.0)

    def inflate(self, pad: float) -> BBox:
        return BBox(self.x0 - pad, self.y0 - pad, self.x1 + pad, self.y1 + pad)

    def union(self, other: BBox) -> BBox:
        return BBox(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


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


def bbox_of(words: list[Word]) -> BBox | None:
    if not words:
        return None
    return BBox(
        min(w.x0 for w in words),
        min(w.y0 for w in words),
        max(w.x1 for w in words),
        max(w.y1 for w in words),
    )


@dataclass
class FieldSpec:
    labels: list[str] = field(default_factory=list)
    direction: str = "auto"
    pattern: str | None = None
    clip: RectFrac | None = None
    relative_to: str = "region"


@dataclass
class HistorySpec:
    expand_left: float = 0.25
    expand_right: float = 0.0
    expand_top: float = 0.05
    expand_bottom: float = 0.0
    region: RectFrac | None = None
    relative_to: str = "page"
    min_rows: int = 2


@dataclass
class TitleBlockLayout:
    id: str
    name: str
    region: RectFrac
    anchors: list[str]
    required_anchor_groups: list[list[str]]
    fields: dict[str, FieldSpec]
    min_score: float = 0.7
    history: HistorySpec = field(default_factory=HistorySpec)


@dataclass
class FilenameFields:
    raw_stem: str
    document_reference: str | None = None
    title: str | None = None
    revision: str | None = None
    suitability: str | None = None
    date: str | None = None
    parts: dict[str, str] = field(default_factory=dict)
    parse_ok: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class ExtractedField:
    name: str
    value: str | None = None
    words: list[Word] = field(default_factory=list)
    source: str = "titleblock"

    @property
    def bbox(self) -> BBox | None:
        return bbox_of(self.words)


@dataclass
class HistoryRow:
    revision: str | None = None
    date: str | None = None
    suitability: str | None = None
    description: str | None = None
    words: list[Word] = field(default_factory=list)

    @property
    def bbox(self) -> BBox | None:
        return bbox_of(self.words)


@dataclass
class RevisionHistory:
    rows: list[HistoryRow] = field(default_factory=list)
    latest: HistoryRow | None = None
    bbox: BBox | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class TitleBlockFields:
    layout_id: str | None = None
    layout_name: str | None = None
    score: float = 0.0
    document_reference: str | None = None
    title: str | None = None
    revision: str | None = None
    suitability: str | None = None
    date: str | None = None
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    history: RevisionHistory = field(default_factory=RevisionHistory)
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
    history_comparisons: list[FieldComparison] = field(default_factory=list)
    status: CheckStatus = CheckStatus.ERROR
    confidence: Confidence = Confidence.REVIEW
    notes: list[str] = field(default_factory=list)
    page_count: int = 0
    error: str | None = None
    preview_png: bytes | None = None
    spelling_errors: list[str] = field(default_factory=list)
    suggested_filename: str | None = None
    original_filename: str = ""
    rename_result: str | None = None
    paired_dwg: Path | None = None
    dwg_mismatch: bool = False
    dwg_files_present: bool = False
    issues: list[CheckStatus] = field(default_factory=list)

    def status_label(self) -> str:
        """Status text for the report: one code, or MULTIPLE plus every issue."""
        issues = [item for item in self.issues if item != CheckStatus.MULTIPLE_ISSUES]
        if not issues:
            return self.status.value
        if len(issues) == 1:
            return issues[0].value
        return "MULTIPLE: " + ", ".join(item.value for item in issues)


def record_issue(result: DocumentResult, status: CheckStatus) -> None:
    if status in (CheckStatus.MATCH, CheckStatus.MULTIPLE_ISSUES):
        return
    if status not in result.issues:
        result.issues.append(status)


def finalize_status(result: DocumentResult) -> None:
    """Collapse recorded issues into status / MULTIPLE_ISSUES."""
    issues = [item for item in result.issues if item not in (CheckStatus.MATCH, CheckStatus.MULTIPLE_ISSUES)]
    if (
        result.status not in (CheckStatus.MATCH, CheckStatus.MULTIPLE_ISSUES)
        and result.status not in issues
    ):
        issues.insert(0, result.status)
    result.issues = issues
    if not issues:
        result.status = CheckStatus.MATCH
        result.confidence = Confidence.HIGH
        return
    result.status = issues[0] if len(issues) == 1 else CheckStatus.MULTIPLE_ISSUES
    result.confidence = Confidence.REVIEW
