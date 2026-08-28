"""Extracteur de cases de BD (panels) par vision classique.

Approche « XY-cut » récursif sur les gouttières (les bandes blanches qui
séparent les cases) :
  1. rogner la marge blanche autour de la région ;
  2. chercher la plus proche gouttière intérieure (horizontale d'abord,
     puis verticale) : une bande de lignes/colonnes quasi-blanches ;
  3. couper le long de cette gouttière et recommencer sur chaque sous-région.

Avantages : léger (OpenCV + numpy), aucun modèle à télécharger, offline, pas de
GPU. Convient très bien aux BD occidentales à gouttières nettes. Les mangas à
cases sans bordure sont gérés « au mieux » (dégradation gracieuse : la page
entière ou de gros blocs). Pour du state-of-the-art (cases + bulles), on
branchera un modèle dédié (Magi, DASS) via la même interface plus tard.

Calcule aussi l'ordre de lecture (gauche→droite pour la BD occidentale,
droite→gauche pour le manga).
"""
from __future__ import annotations

import base64

import cv2
import fitz  # type: ignore
import numpy as np

from .schema import PagePanels, Panel

# --- Paramètres réglables --------------------------------------------------- #
_RENDER_WIDTH = 1000       # largeur de rendu de la page pour l'analyse (px)
_WHITE_THR = 235           # un pixel >= seuil (0..255) est considéré « blanc »
_GUTTER_FRAC = 0.97        # fraction de blanc pour qu'une ligne soit gouttière
_MIN_GUTTER_PX = 6         # épaisseur minimale d'une gouttière
_MIN_PANEL_FRAC = 0.012    # aire minimale d'une case (fraction de la page)
_MIN_SIDE_PX = 40          # côté minimal d'une case
_MAX_DEPTH = 14
_THUMB_WIDTH = 420         # largeur de la miniature renvoyée à l'UI


def _content_bbox(white_mask: np.ndarray) -> tuple[int, int, int, int] | None:
    """BBox du contenu (non-blanc) dans un masque booléen `white_mask`."""
    content = ~white_mask
    rows = np.where(content.any(axis=1))[0]
    cols = np.where(content.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _interior_bands(profile: np.ndarray, frac: float, min_len: int) -> list[tuple[int, int]]:
    """Bandes intérieures où `profile >= frac` (gouttières candidates)."""
    white = profile >= frac
    bands: list[tuple[int, int]] = []
    i, n = 0, len(white)
    while i < n:
        if white[i]:
            j = i
            while j < n and white[j]:
                j += 1
            bands.append((i, j))
            i = j
        else:
            i += 1
    # on écarte les bandes qui touchent les bords (déjà rognées) et trop fines
    return [(s, e) for (s, e) in bands if s > 0 and e < n and (e - s) >= min_len]


def _segments_between(length: int, bands: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Segments de contenu entre les gouttières (gouttières exclues)."""
    segs: list[tuple[int, int]] = []
    prev = 0
    for s, e in bands:
        if s - prev > 0:
            segs.append((prev, s))
        prev = e
    if length - prev > 0:
        segs.append((prev, length))
    return segs


def _cut(white: np.ndarray, x0: int, y0: int, x1: int, y1: int, direction: str,
         depth: int) -> list[tuple[int, int, int, int]]:
    """Segmente récursivement la région [x0,y0,x1,y1) → liste de bbox de cases."""
    region = white[y0:y1, x0:x1]
    if region.size == 0:
        return []

    # 1) rogner la marge blanche.
    bbox = _content_bbox(region)
    if bbox is None:
        return []
    cx0, cy0, cx1, cy1 = bbox
    x0, y0, x1, y1 = x0 + cx0, y0 + cy0, x0 + cx1, y0 + cy1
    region = white[y0:y1, x0:x1]
    h, w = region.shape

    if h < _MIN_SIDE_PX or w < _MIN_SIDE_PX or depth > _MAX_DEPTH:
        return [(x0, y0, x1, y1)]

    # 2) gouttières horizontales (lignes majoritairement blanches).
    row_white = region.mean(axis=1) / 255.0
    h_bands = _interior_bands(row_white, _GUTTER_FRAC, _MIN_GUTTER_PX)
    if h_bands:
        out: list[tuple[int, int, int, int]] = []
        for s, e in _segments_between(h, h_bands):
            out += _cut(white, x0, y0 + s, x1, y0 + e, direction, depth + 1)
        return out

    # 3) sinon gouttières verticales (colonnes majoritairement blanches).
    col_white = region.mean(axis=0) / 255.0
    v_bands = _interior_bands(col_white, _GUTTER_FRAC, _MIN_GUTTER_PX)
    if v_bands:
        segs = _segments_between(w, v_bands)
        if direction == "rtl":          # manga : on lit de droite à gauche
            segs = list(reversed(segs))
        out = []
        for s, e in segs:
            out += _cut(white, x0 + s, y0, x0 + e, y1, direction, depth + 1)
        return out

    # 4) région atomique = une case.
    return [(x0, y0, x1, y1)]


def _render_page(page: "fitz.Page", width: int) -> np.ndarray:
    """Rend une page PDF en image RGB (numpy) à la largeur voulue."""
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    return img


def segment_page(page: "fitz.Page", direction: str = "ltr", with_thumbnail: bool = True) -> PagePanels:
    img = _render_page(page, _RENDER_WIDTH)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    white = (gray >= _WHITE_THR).astype(np.uint8) * 255  # 255=blanc, 0=contenu
    H, W = gray.shape

    boxes = _cut(white, 0, 0, W, H, direction, 0)

    page_area = float(W * H)
    min_area = _MIN_PANEL_FRAC * page_area
    panels: list[Panel] = []
    idx = 0
    for (bx0, by0, bx1, by1) in boxes:
        area = (bx1 - bx0) * (by1 - by0)
        if area < min_area:
            continue
        panels.append(Panel(
            index=idx,
            x=round(bx0 / W, 4),
            y=round(by0 / H, 4),
            w=round((bx1 - bx0) / W, 4),
            h=round((by1 - by0) / H, 4),
            area_ratio=round(area / page_area, 4),
        ))
        idx += 1

    result = PagePanels(
        page_index=page.number,
        reading_direction=direction,
        panel_count=len(panels),
        panels=panels,
    )

    if with_thumbnail:
        scale = _THUMB_WIDTH / W
        thumb = cv2.resize(img, (_THUMB_WIDTH, int(H * scale)))
        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(thumb, cv2.COLOR_RGB2BGR),
                               [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            result.thumbnail = base64.b64encode(buf).decode("ascii")
            result.thumb_width = thumb.shape[1]
            result.thumb_height = thumb.shape[0]

    return result


def extract_panels(pdf_bytes: bytes, direction: str = "ltr", max_pages: int = 12,
                   with_thumbnails: bool = True) -> list[PagePanels]:
    """Segmente les cases des premières `max_pages` planches d'un PDF de BD."""
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PagePanels] = []
    try:
        for i, page in enumerate(pdf):
            if i >= max_pages:
                break
            pages.append(segment_page(page, direction=direction, with_thumbnail=with_thumbnails))
    finally:
        pdf.close()
    return pages
