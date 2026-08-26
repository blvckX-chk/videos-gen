"""Composer : Composition (déclarative) → Image PIL finale.

Chaque Layer est rendue puis collée sur le canvas dans l'ordre déclaré,
avec ancrage + offset + opacité + coins arrondis pour les images.
"""
from __future__ import annotations

import io
from pathlib import Path

import httpx
from PIL import Image

from .processing import (
    apply_corner_radius,
    draw_text_block,
    fit_contain,
    fit_cover,
    gradient,
    load_font,
    _parse_color,
)
from .schema import Anchor, Composition, FORMAT_DIMS, ImageFormat, Layer, LayerType
from .storage import asset_path, get_asset


def _canvas_size(comp: Composition) -> tuple[int, int]:
    if comp.width and comp.height:
        return comp.width, comp.height
    return FORMAT_DIMS[ImageFormat(comp.format)]


def _anchor_pos(anchor: Anchor, canvas: tuple[int, int], size: tuple[int, int]) -> tuple[int, int]:
    cw, ch = canvas
    lw, lh = size
    ax = {"left": 0, "center": (cw - lw) // 2, "right": cw - lw}
    ay = {"top": 0, "middle": (ch - lh) // 2, "bottom": ch - lh}
    mapping = {
        Anchor.TOP_LEFT: (ax["left"], ay["top"]),
        Anchor.TOP: (ax["center"], ay["top"]),
        Anchor.TOP_RIGHT: (ax["right"], ay["top"]),
        Anchor.LEFT: (ax["left"], ay["middle"]),
        Anchor.CENTER: (ax["center"], ay["middle"]),
        Anchor.RIGHT: (ax["right"], ay["middle"]),
        Anchor.BOTTOM_LEFT: (ax["left"], ay["bottom"]),
        Anchor.BOTTOM: (ax["center"], ay["bottom"]),
        Anchor.BOTTOM_RIGHT: (ax["right"], ay["bottom"]),
    }
    return mapping[anchor]


def _load_layer_image(layer: Layer) -> Image.Image:
    if layer.asset_id:
        a = get_asset(layer.asset_id)
        if a is None:
            raise ValueError(f"Asset introuvable : {layer.asset_id}")
        for ext in ("png", "jpg", "webp"):
            p = asset_path(layer.asset_id, ext)
            if p.exists():
                return Image.open(p).convert("RGBA")
        raise FileNotFoundError(f"Fichier de l'asset introuvable : {layer.asset_id}")
    if layer.asset_url and layer.asset_url.startswith(("http://", "https://")):
        r = httpx.get(layer.asset_url, timeout=30)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    if layer.asset_url and layer.asset_url.startswith("/"):
        # URL relative (locale au backend) → chercher le fichier
        from ..render.service import storage_root
        p = storage_root() / layer.asset_url.lstrip("/")
        return Image.open(p).convert("RGBA")
    raise ValueError("Layer image sans asset_id ni asset_url utilisable.")


def compose(comp: Composition) -> Image.Image:
    """Rend une composition en image RGBA finale."""
    cw, ch = _canvas_size(comp)
    canvas = Image.new("RGBA", (cw, ch), _parse_color(comp.background))

    for layer in comp.layers:
        # Rend la couche seule dans son propre buffer RGBA
        if layer.type == LayerType.SOLID:
            w = layer.width or cw
            h = layer.height or ch
            buf = Image.new("RGBA", (w, h), _parse_color(layer.color or "#000000"))
        elif layer.type == LayerType.GRADIENT:
            w = layer.width or cw
            h = layer.height or ch
            buf = gradient((w, h), layer.color or "#000", layer.color2 or "#FFF",
                           layer.gradient_angle)
        elif layer.type == LayerType.IMAGE:
            src = _load_layer_image(layer)
            w = layer.width or src.width
            h = layer.height or src.height
            if layer.fit == "contain":
                buf = fit_contain(src, w, h)
            elif layer.fit == "stretch":
                buf = src.resize((w, h), Image.LANCZOS)
            else:
                buf = fit_cover(src, w, h)
            if layer.corner_radius:
                buf = apply_corner_radius(buf, layer.corner_radius)
        elif layer.type == LayerType.TEXT:
            font = load_font(layer.font_weight, layer.font_size)
            max_w = layer.max_width or (cw - 80)
            # buffer temporaire assez grand pour mesurer
            tmp = Image.new("RGBA", (max_w + 40, cw), (0, 0, 0, 0))
            used_w, used_h = draw_text_block(
                tmp, layer.text or "", (0, 0), font,
                layer.text_color, max_w,
                align=layer.text_align, line_height=layer.line_height,
                stroke_color=layer.stroke_color, stroke_width=layer.stroke_width,
                shadow=layer.shadow,
            )
            buf = tmp.crop((0, 0, min(used_w or 1, max_w), used_h))
        elif layer.type == LayerType.SHAPE:
            from PIL import ImageDraw
            w = layer.width or 100
            h = layer.height or 100
            buf = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(buf)
            fill = _parse_color(layer.fill) if layer.fill else None
            stroke = _parse_color(layer.stroke) if layer.stroke else None
            if layer.shape == "circle":
                d.ellipse((0, 0, w - 1, h - 1), fill=fill, outline=stroke,
                          width=layer.stroke_width or 0)
            else:
                d.rectangle((0, 0, w - 1, h - 1), fill=fill, outline=stroke,
                            width=layer.stroke_width or 0)
        else:
            continue  # type inconnu, on ignore

        if layer.opacity < 1.0:
            alpha = buf.split()[-1]
            alpha = alpha.point(lambda a, o=layer.opacity: int(a * o))
            buf.putalpha(alpha)

        pos = _anchor_pos(layer.anchor, (cw, ch), buf.size)
        canvas.alpha_composite(buf, dest=(pos[0] + layer.dx, pos[1] + layer.dy))

    return canvas


def apply_watermark(img: Image.Image, text: str, template_accent: str = "#E4A93E") -> Image.Image:
    """Watermark discret en bas — même identité que la vidéo."""
    from PIL import ImageDraw
    canvas = img.convert("RGBA")
    font = load_font("bold", max(14, canvas.width // 60))
    bbox = font.getbbox(text.upper())
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 18, 8
    pill = Image.new("RGBA", (tw + pad_x * 2, th + pad_y * 2), (0, 0, 0, 96))
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle((0, 0, pill.width, pill.height), radius=pill.height // 2,
                        outline=(*_parse_color(template_accent)[:3], 200), width=2)
    d.text((pad_x, pad_y - 2), text.upper(), font=font, fill=(255, 255, 255, 220))
    x = (canvas.width - pill.width) // 2
    y = canvas.height - pill.height - 28
    canvas.alpha_composite(pill, (x, y))
    return canvas
