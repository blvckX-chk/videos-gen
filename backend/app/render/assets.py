"""Pré-rasterisation des pages/cases pour le rendu Remotion.

Remotion consomme des URLs http/file. On produit à la demande les images JPEG
dont chaque shot a besoin (page entière ou case rognée), on les met dans
`storage/assets/<doc_id>/` et on injecte leur URL dans le storyboard sous
`shot.asset_url` avant d'appeler le moteur de rendu.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import fitz  # type: ignore
import numpy as np

from ..ingestion.schema import Document, PagePanels
from ..services.documents import get_document_bytes
from ..storyboard.schema import ShotType, Storyboard

_PAGE_WIDTH = 1400          # rendu haute qualité (Ken Burns : marge de zoom)
_PANEL_WIDTH = 1200


def storage_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "storage"
    root.mkdir(exist_ok=True)
    return root


def _asset_dir(doc_id: str) -> Path:
    d = storage_root() / "assets" / doc_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _render_page(pdf: "fitz.Document", page_index: int, width: int) -> np.ndarray:
    page = pdf[page_index]
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    return img


def _write_jpeg(img: np.ndarray, path: Path) -> None:
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError(f"Encodage JPEG échoué pour {path}")
    path.write_bytes(buf.tobytes())


def prepare_assets(doc: Document, sb: Storyboard, base_url: str) -> Storyboard:
    """Rasterise les pages/cases nécessaires et renvoie une copie du storyboard
    avec `shot.asset_url` renseigné. `base_url` = URL absolue vers /assets."""
    raw = get_document_bytes(doc.id)
    if raw is None:
        return sb  # rien à faire (extraits texte-only : aucun asset requis)

    pdf = fitz.open(stream=raw, filetype="pdf")
    out = sb.model_copy(deep=True)
    dir_ = _asset_dir(doc.id)

    # Index des cases par (page_index, panel_index) pour éviter les recalculs.
    panels_by_page: dict[int, PagePanels] = {p.page_index: p for p in (doc.panels or [])}
    rendered_pages: dict[int, np.ndarray] = {}

    def page_img(idx: int) -> np.ndarray:
        if idx not in rendered_pages:
            rendered_pages[idx] = _render_page(pdf, idx, _PAGE_WIDTH)
        return rendered_pages[idx]

    for scene in out.scenes:
        for shot in scene.shots:
            if shot.type == ShotType.PAGE and shot.source_page is not None:
                fname = f"page_{shot.source_page:03d}.jpg"
                fpath = dir_ / fname
                if not fpath.exists():
                    _write_jpeg(page_img(shot.source_page), fpath)
                shot.asset_url = f"{base_url}/{doc.id}/{fname}"
            elif shot.type == ShotType.PANEL and shot.source_page is not None:
                pi = shot.source_page
                pj = shot.source_panel
                fname = f"panel_{pi:03d}_{pj:03d}.jpg"
                fpath = dir_ / fname
                if not fpath.exists():
                    pg = panels_by_page.get(pi)
                    if pg is None or pj is None or pj >= len(pg.panels):
                        continue
                    panel = pg.panels[pj]
                    img = _render_page(pdf, pi, _PANEL_WIDTH)
                    H, W = img.shape[:2]
                    x0 = int(panel.x * W)
                    y0 = int(panel.y * H)
                    x1 = int((panel.x + panel.w) * W)
                    y1 = int((panel.y + panel.h) * H)
                    _write_jpeg(img[y0:y1, x0:x1], fpath)
                shot.asset_url = f"{base_url}/{doc.id}/{fname}"

    pdf.close()
    return out
