import base64
import io
import re
import asyncio
import ipaddress
from urllib.parse import urlparse
from typing import List, Optional, Tuple

import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.limiter import limiter


router = APIRouter(prefix="/images", tags=["images"])


class ResultsCardRequest(BaseModel):
    edition: str = Field(..., pattern="^(anime|movies|tv_shows)$")
    mode: str = Field(..., min_length=1, max_length=32)
    keep_images: List[str] = Field(..., min_length=4, max_length=4, description="4 image URLs or data URIs")
    cut_images: List[str] = Field(..., min_length=4, max_length=4, description="4 image URLs or data URIs")
    width: int = Field(900, ge=640, le=1600)


_DATA_URI_RE = re.compile(r"^data:image/(?P<fmt>png|jpe?g|webp);base64,(?P<data>[A-Za-z0-9+/=]+)$", re.I)


def _require_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: WPS433
    except ModuleNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail="Pillow is required for this endpoint. Install it with: pip install pillow",
        ) from e
    return Image, ImageDraw, ImageFont, ImageOps


def _hex(color: str) -> Tuple[int, int, int, int]:
    color = color.lstrip("#")
    if len(color) == 6:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        return (r, g, b, 255)
    raise ValueError(f"Unsupported color: {color}")


def _load_font(ImageFont, size: int, bold: bool = False):
    # Pillow wheels usually ship DejaVu fonts.
    try:
        import PIL  # noqa: WPS433

        font_dir = getattr(PIL, "__path__", [None])[0]
        if font_dir:
            font_path = f"{font_dir}/fonts/DejaVuSans{'-Bold' if bold else ''}.ttf"
            return ImageFont.truetype(font_path, size)
    except Exception:
        pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


async def _fetch_image_bytes_http(
    session: aiohttp.ClientSession,
    url: str,
    max_bytes: int,
) -> bytes:
    async with session.get(url) as resp:
        if resp.status != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch image: {url}")
        total = 0
        chunks: List[bytes] = []
        async for chunk in resp.content.iter_chunked(64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(status_code=400, detail="Image too large")
            chunks.append(chunk)
        return b"".join(chunks)


def _validate_remote_url(url: str) -> None:
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Images must be http(s) URLs or data:image/...;base64,...")

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise HTTPException(status_code=400, detail="Invalid image URL")
    if host in {"localhost"}:
        raise HTTPException(status_code=400, detail="Refusing to fetch from localhost")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise HTTPException(status_code=400, detail="Refusing to fetch from private IP ranges")
    except ValueError:
        pass


async def _fetch_image_bytes(
    session: aiohttp.ClientSession,
    url_or_data: str,
    max_bytes: int = 10_000_000,
) -> bytes:
    m = _DATA_URI_RE.match(url_or_data.strip())
    if m:
        try:
            return base64.b64decode(m.group("data"), validate=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid base64 data URI") from e

    _validate_remote_url(url_or_data)
    return await _fetch_image_bytes_http(session, url_or_data, max_bytes=max_bytes)


def _rounded_mask(Image, ImageDraw, size: Tuple[int, int], radius: int):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def _safe_open(Image, ImageOps, blob: bytes):
    try:
        im = Image.open(io.BytesIO(blob))
        im = ImageOps.exif_transpose(im)
        return im.convert("RGBA")
    except Exception:
        return None


def _placeholder_tile(Image, ImageDraw, size: Tuple[int, int], bg_rgba: Tuple[int, int, int, int], fg_rgba: Tuple[int, int, int, int]):
    tile = Image.new("RGBA", size, bg_rgba)
    d = ImageDraw.Draw(tile)
    pad = max(8, size[0] // 18)
    d.rectangle((pad, pad, size[0] - pad, size[1] - pad), outline=fg_rgba, width=max(3, size[0] // 70))
    d.line((pad, pad, size[0] - pad, size[1] - pad), fill=fg_rgba, width=max(3, size[0] // 70))
    d.line((size[0] - pad, pad, pad, size[1] - pad), fill=fg_rgba, width=max(3, size[0] // 70))
    return tile


def _draw_results_card(
    edition: str,
    mode: str,
    keep_imgs: List[Optional["Image.Image"]],
    cut_imgs: List[Optional["Image.Image"]],
    width: int,
):
    Image, ImageDraw, ImageFont, ImageOps = _require_pillow()

    PEACH = _hex("#fff3e0")
    TERRACOTTA = _hex("#e07a5f")
    TEAL = _hex("#3d5a80")
    CORAL = _hex("#ee6c4d")
    SKY = _hex("#98c1d9")
    BODY = _hex("#2d2d2d")
    BORDER = _hex("#e2e1de")
    WHITE = (255, 255, 255, 255)

    padding = int(width * 0.06)
    card_w = width

    header_h = int(width * 0.13)
    section_label_h = int(width * 0.05)
    gap = int(width * 0.018)
    inner_gap = int(width * 0.015)
    tile_radius = max(18, width // 45)
    card_radius = max(26, width // 35)

    content_margin = int(width * 0.03)
    content_w = card_w - (padding * 2) - (content_margin * 2)

    # 1x4 poster row per section (more compact overall height)
    tile_w = int((content_w - inner_gap * 3) / 4)
    tile_h = int(tile_w * 1.25)

    section_h = section_label_h + gap + tile_h
    height = padding * 2 + header_h + gap + section_h + gap + section_h

    base = Image.new("RGBA", (card_w, height), PEACH)
    d = ImageDraw.Draw(base)

    # Background accents (subtle circles)
    accent_alpha = 35
    for (x, y, r, col) in [
        (int(card_w * 0.10), int(height * 0.12), int(width * 0.14), TERRACOTTA),
        (int(card_w * 0.88), int(height * 0.22), int(width * 0.18), TEAL),
        (int(card_w * 0.18), int(height * 0.78), int(width * 0.20), CORAL),
    ]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=(col[0], col[1], col[2], accent_alpha))

    # White card
    card_box = (padding, padding, card_w - padding, height - padding)
    d.rounded_rectangle(card_box, radius=card_radius, fill=WHITE, outline=BORDER, width=3)

    def fit_font(text: str, max_width: int, start_size: int, min_size: int) -> "ImageFont.ImageFont":
        size = start_size
        while size >= min_size:
            f = _load_font(ImageFont, size=size, bold=True)
            box = d.textbbox((0, 0), text, font=f)
            if (box[2] - box[0]) <= max_width:
                return f
            size -= 2
        return _load_font(ImageFont, size=min_size, bold=True)

    subtitle_font = _load_font(ImageFont, size=int(width * 0.026), bold=False)
    label_font = _load_font(ImageFont, size=int(width * 0.030), bold=True)

    safe_edition = edition.replace("_", " ").title()
    safe_mode = mode.strip().lower()
    title = f"Keep/Cut - {safe_edition} edition - {safe_mode} mode"

    title_x = padding + int(width * 0.035)
    title_y = padding + int(width * 0.030)
    title_max_w = (card_w - padding - int(width * 0.035)) - title_x
    title_font = fit_font(title, max_width=title_max_w, start_size=int(width * 0.034), min_size=int(width * 0.022))
    d.text((title_x, title_y), title, fill=TERRACOTTA, font=title_font)
    d.text((title_x, title_y + int(width * 0.055)), "4 keeps • 4 cuts", fill=BODY, font=subtitle_font)

    grid_left = padding + content_margin

    def draw_section(top: int, label: str, label_color: Tuple[int, int, int, int], imgs: List[Optional["Image.Image"]]):
        # Label pill
        pill_w = int(content_w * 0.34)
        pill_h = section_label_h
        pill_x0 = grid_left
        pill_y0 = top
        pill_x1 = pill_x0 + pill_w
        pill_y1 = pill_y0 + pill_h
        d.rounded_rectangle((pill_x0, pill_y0, pill_x1, pill_y1), radius=pill_h // 2, fill=label_color)
        d.text((pill_x0 + pill_h // 2, pill_y0 + int(pill_h * 0.18)), label, fill=WHITE, font=label_font)

        grid_top = pill_y1 + gap
        tiles = []
        for im in imgs:
            if im is None:
                tiles.append(_placeholder_tile(Image, ImageDraw, (tile_w, tile_h), SKY, label_color))
            else:
                tiles.append(ImageOps.fit(im, (tile_w, tile_h), centering=(0.5, 0.3)))

        # Paste 1x4 row with rounded corners
        mask = _rounded_mask(Image, ImageDraw, (tile_w, tile_h), radius=tile_radius)
        coords = [(grid_left + i * (tile_w + inner_gap), grid_top) for i in range(4)]
        for tile, (x, y) in zip(tiles, coords, strict=True):
            base.paste(tile, (x, y), mask)
            d.rounded_rectangle((x, y, x + tile_w, y + tile_h), radius=tile_radius, outline=(label_color[0], label_color[1], label_color[2], 170), width=4)

        return grid_top + tile_h

    keep_top = padding + header_h
    keep_end = draw_section(keep_top, "KEEPS", TEAL, keep_imgs)
    cut_top = keep_end + gap
    draw_section(cut_top, "CUTS", CORAL, cut_imgs)

    return base.convert("RGBA")


@router.post("/results-card")
@limiter.limit("30/minute")
async def results_card(req: ResultsCardRequest, request: Request):
    Image, ImageDraw, ImageFont, ImageOps = _require_pillow()

    timeout = aiohttp.ClientTimeout(total=8.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        keep_blobs = await asyncio.gather(
            *[_fetch_image_bytes(session, u) for u in req.keep_images],
            return_exceptions=True,
        )
        cut_blobs = await asyncio.gather(
            *[_fetch_image_bytes(session, u) for u in req.cut_images],
            return_exceptions=True,
        )

    for idx, res in enumerate(keep_blobs):
        if isinstance(res, Exception):
            raise HTTPException(status_code=400, detail=f"keep_images[{idx}] could not be loaded") from res
    for idx, res in enumerate(cut_blobs):
        if isinstance(res, Exception):
            raise HTTPException(status_code=400, detail=f"cut_images[{idx}] could not be loaded") from res

    keep_imgs: List[Optional["Image.Image"]] = []
    for idx, blob in enumerate(keep_blobs):
        im = _safe_open(Image, ImageOps, blob)  # type: ignore[arg-type]
        if im is None:
            raise HTTPException(status_code=400, detail=f"keep_images[{idx}] is not a valid image")
        keep_imgs.append(im)

    cut_imgs: List[Optional["Image.Image"]] = []
    for idx, blob in enumerate(cut_blobs):
        im = _safe_open(Image, ImageOps, blob)  # type: ignore[arg-type]
        if im is None:
            raise HTTPException(status_code=400, detail=f"cut_images[{idx}] is not a valid image")
        cut_imgs.append(im)

    img = _draw_results_card(req.edition, req.mode, keep_imgs, cut_imgs, req.width)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    png = out.getvalue()

    safe_mode = re.sub(r"[^a-z0-9_-]+", "_", req.mode.strip().lower())
    filename = f"keepcut_{req.edition}_{safe_mode}.png"
    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
    return Response(content=png, media_type="image/png", headers=headers)
