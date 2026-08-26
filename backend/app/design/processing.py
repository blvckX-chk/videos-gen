"""Opérations de traitement d'images (déterministes, sans réseau).

Toutes les opérations manipulent des `PIL.Image` en RGBA en interne pour ne
jamais perdre la transparence, puis exportent en PNG (préserve l'alpha) ou
JPEG (aplati sur fond blanc).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------- #
# Sauvegarde / probing
# --------------------------------------------------------------------------- #
def save_image(img: Image.Image, out: Path, quality: int = 92) -> Tuple[int, int, int]:
    """Sauve PNG si alpha présent, JPEG sinon. Renvoie (w, h, size_bytes)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        rgb = _flatten(img, "#FFFFFF")
        rgb.save(out, "JPEG", quality=quality, optimize=True)
    else:
        img.save(out, "PNG", optimize=True)
    return img.width, img.height, out.stat().st_size


def _flatten(img: Image.Image, bg: str) -> Image.Image:
    if img.mode != "RGBA":
        return img.convert("RGB")
    canvas = Image.new("RGB", img.size, bg)
    canvas.paste(img, mask=img.split()[-1])
    return canvas


# --------------------------------------------------------------------------- #
# Redimensionnement / recadrage intelligent
# --------------------------------------------------------------------------- #
def fit_cover(img: Image.Image, w: int, h: int, focus: tuple[float, float] = (0.5, 0.4)) -> Image.Image:
    """Remplit (w, h) en couvrant intégralement, avec un focus par défaut
    proche du tiers supérieur (règle des tiers — pratique pour les portraits)."""
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        # source trop large → on scale par la hauteur
        new_h = h
        new_w = round(new_h * src_ratio)
    else:
        new_w = w
        new_h = round(new_w / src_ratio)
    scaled = img.resize((new_w, new_h), Image.LANCZOS)
    fx, fy = focus
    cx = int(fx * new_w)
    cy = int(fy * new_h)
    left = max(0, min(cx - w // 2, new_w - w))
    top = max(0, min(cy - h // 2, new_h - h))
    return scaled.crop((left, top, left + w, top + h))


def fit_contain(img: Image.Image, w: int, h: int, bg: str = "#00000000") -> Image.Image:
    """Redimensionne pour tenir dans (w, h) sans rogner, remplit le reste."""
    src_ratio = img.width / img.height
    dst_ratio = w / h
    if src_ratio > dst_ratio:
        new_w = w
        new_h = round(new_w / src_ratio)
    else:
        new_h = h
        new_w = round(new_h * src_ratio)
    scaled = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), bg)
    canvas.paste(scaled, ((w - new_w) // 2, (h - new_h) // 2), scaled if scaled.mode == "RGBA" else None)
    return canvas


# --------------------------------------------------------------------------- #
# Formes utilitaires
# --------------------------------------------------------------------------- #
def rounded_rect_mask(size: tuple[int, int], radius: int) -> Image.Image:
    w, h = size
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    return m


def apply_corner_radius(img: Image.Image, radius: int) -> Image.Image:
    if radius <= 0:
        return img
    img = img.convert("RGBA")
    mask = rounded_rect_mask(img.size, radius)
    if "A" in img.mode:
        alpha = img.split()[-1]
        combined = Image.new("L", img.size)
        combined.paste(mask, mask=alpha)
        img.putalpha(combined)
    else:
        img.putalpha(mask)
    return img


# --------------------------------------------------------------------------- #
# Dégradés
# --------------------------------------------------------------------------- #
def gradient(size: tuple[int, int], color1: str, color2: str, angle_deg: float = 90.0) -> Image.Image:
    """Dégradé linéaire, angle en degrés (0 = horizontal G→D, 90 = vertical bas→haut)."""
    w, h = size
    c1 = _parse_color(color1)
    c2 = _parse_color(color2)
    rad = math.radians(angle_deg)
    dx = math.cos(rad); dy = -math.sin(rad)
    # projeter chaque pixel sur la direction, normaliser 0..1
    img = Image.new("RGBA", size)
    px = img.load()
    minv = min(0, dx * (w - 1), dy * (h - 1), dx * (w - 1) + dy * (h - 1))
    maxv = max(0, dx * (w - 1), dy * (h - 1), dx * (w - 1) + dy * (h - 1))
    span = (maxv - minv) or 1
    for y in range(h):
        for x in range(w):
            t = (dx * x + dy * y - minv) / span
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            a = int(c1[3] + (c2[3] - c1[3]) * t)
            px[x, y] = (r, g, b, a)
    return img


def _parse_color(c: str) -> tuple[int, int, int, int]:
    c = c.strip()
    if c.startswith("#"):
        c = c[1:]
    if len(c) == 6:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)
    if len(c) == 8:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), int(c[6:8], 16))
    if len(c) == 3:
        return tuple(int(ch * 2, 16) for ch in c) + (255,)  # type: ignore
    raise ValueError(f"Couleur invalide : #{c}")


# --------------------------------------------------------------------------- #
# Typographie
# --------------------------------------------------------------------------- #
_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]
_FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]


def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    key = (weight, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    paths = _FONT_CANDIDATES_BOLD if weight == "bold" else _FONT_CANDIDATES_REGULAR
    for p in paths:
        if Path(p).exists():
            font = ImageFont.truetype(p, size)
            _FONT_CACHE[key] = font
            return font
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap simple sur les mots, respecte les \n existants."""
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        words = para.split()
        if not words:
            lines.append("")
            continue
        cur = words[0]
        for w in words[1:]:
            trial = f"{cur} {w}"
            bbox = font.getbbox(trial)
            if bbox[2] - bbox[0] <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_text_block(
    canvas: Image.Image, text: str, xy: tuple[int, int],
    font: ImageFont.FreeTypeFont, color: str, max_width: int,
    align: str = "left", line_height: float = 1.1,
    stroke_color: str | None = None, stroke_width: int = 0, shadow: bool = False,
) -> tuple[int, int]:
    """Dessine le texte dans le canvas, renvoie (largeur_utilisée, hauteur_utilisée)."""
    lines = wrap_text(text, font, max_width)
    line_h = int((font.getbbox("Hg")[3] - font.getbbox("Hg")[1]) * line_height)
    d = ImageDraw.Draw(canvas)
    x0, y0 = xy
    max_line_w = 0
    for i, ln in enumerate(lines):
        bbox = font.getbbox(ln)
        w = bbox[2] - bbox[0]
        max_line_w = max(max_line_w, w)
        if align == "center":
            lx = x0 + (max_width - w) // 2
        elif align == "right":
            lx = x0 + (max_width - w)
        else:
            lx = x0
        ly = y0 + i * line_h
        if shadow:
            d.text((lx + 3, ly + 3), ln, font=font, fill=(0, 0, 0, 150))
        if stroke_color and stroke_width > 0:
            d.text((lx, ly), ln, font=font, fill=color,
                   stroke_width=stroke_width, stroke_fill=stroke_color)
        else:
            d.text((lx, ly), ln, font=font, fill=color)
    return max_line_w, line_h * len(lines)


# --------------------------------------------------------------------------- #
# Retrait de fond (rembg) — chargement paresseux pour ne pas bloquer l'import.
# --------------------------------------------------------------------------- #
_REMBG_SESSION = None


def rembg_available() -> bool:
    try:
        import rembg  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


def remove_background(img: Image.Image) -> Image.Image:
    """Isole le sujet d'une image, renvoie RGBA avec fond transparent.
    Utilise `rembg` (u2net) — modèle téléchargé au premier appel (~170 Mo)."""
    global _REMBG_SESSION
    if not rembg_available():
        raise RuntimeError("rembg n'est pas installé (`pip install rembg[cpu]`).")
    from rembg import new_session, remove  # type: ignore
    if _REMBG_SESSION is None:
        _REMBG_SESSION = new_session("u2net")
    result = remove(img.convert("RGBA"), session=_REMBG_SESSION)
    return result if isinstance(result, Image.Image) else Image.open(result)
