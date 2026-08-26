from __future__ import annotations

from io import BytesIO

from drawing_qa.extract import require_pymupdf
from drawing_qa.models import ExtractedField, TitleBlockFields

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]


PREVIEW_PANELS = (
    ("document_reference", "Doc ref", 168),
    ("title", "Title", 176),
    ("revision", "Rev", 64),
    ("suitability", "Status", 96),
    ("date", "Date", 88),
)
PREVIEW_HEIGHT = 78
PREVIEW_GAP = 4
CAPTION_H = 12


def preview_size() -> tuple[int, int]:
    width = PREVIEW_GAP + sum(panel[2] + PREVIEW_GAP for panel in PREVIEW_PANELS)
    return width, PREVIEW_HEIGHT


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _crop_field(page, field: ExtractedField, zoom: float = 2.0) -> Image.Image | None:
    if Image is None or not field.bbox:
        return None
    require_pymupdf()
    import pymupdf

    box = field.bbox.inflate(8)
    clip = pymupdf.Rect(box.x0, box.y0, box.x1, box.y1)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def render_preview(page, titleblock: TitleBlockFields) -> bytes | None:
    if Image is None:
        return None
    width, height = preview_size()
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    caption_font = _font(9)
    x = PREVIEW_GAP
    for name, caption, panel_w in PREVIEW_PANELS:
        y = PREVIEW_GAP
        box = (x, y, x + panel_w - 1, height - PREVIEW_GAP - 1)
        draw.rectangle(box, outline=(180, 180, 180), width=1)
        draw.text((x + 3, y + 1), caption, fill=(80, 80, 80), font=caption_font)
        field = titleblock.fields.get(name) or ExtractedField(name)
        crop = _crop_field(page, field)
        inner = (x + 2, y + CAPTION_H, x + panel_w - 2, height - PREVIEW_GAP - 2)
        inner_w = inner[2] - inner[0]
        inner_h = inner[3] - inner[1]
        if crop is not None:
            crop.thumbnail((inner_w, inner_h), Image.Resampling.LANCZOS)
            ox = inner[0] + (inner_w - crop.width) // 2
            oy = inner[1] + (inner_h - crop.height) // 2
            canvas.paste(crop, (ox, oy))
        else:
            draw.text((x + 6, y + 28), "—", fill=(160, 160, 160), font=_font(16))
        x += panel_w + PREVIEW_GAP
    buffer = BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
