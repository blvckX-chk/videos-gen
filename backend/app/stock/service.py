"""Recherche et import de médias libres (Pexels, Pixabay).

Dégradation gracieuse : une source sans clé API est simplement ignorée.
Les résultats des sources disponibles sont fusionnés.
"""
from __future__ import annotations

import logging

import httpx

from ..config import get_settings
from .schema import StockItem

logger = logging.getLogger("videos_gen.stock")

_TIMEOUT = httpx.Timeout(20.0)


def available_sources() -> list[str]:
    s = get_settings()
    out = []
    if s.pexels_api_key:
        out.append("pexels")
    if s.pixabay_api_key:
        out.append("pixabay")
    return out


# --------------------------------------------------------------- Pexels --- #
async def _pexels(query: str, kind: str, per_page: int) -> list[StockItem]:
    key = get_settings().pexels_api_key
    if not key:
        return []
    headers = {"Authorization": key}
    items: list[StockItem] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as c:
        if kind == "video":
            r = await c.get("https://api.pexels.com/videos/search",
                            params={"query": query, "per_page": per_page})
            r.raise_for_status()
            for v in r.json().get("videos", []):
                files = sorted(v.get("video_files", []),
                               key=lambda f: (f.get("width") or 0))
                # on vise ~720-1080p : le plus grand <= 1920, sinon le plus grand
                pick = next((f for f in reversed(files) if (f.get("width") or 0) <= 1920),
                            files[-1] if files else None)
                if not pick:
                    continue
                items.append(StockItem(
                    id=f"pexels:{v['id']}", source="pexels", kind="video",
                    thumb=v.get("image", ""), download_url=pick["link"],
                    width=pick.get("width") or 0, height=pick.get("height") or 0,
                    duration=float(v.get("duration") or 0) or None,
                    author=(v.get("user") or {}).get("name", ""),
                    author_url=(v.get("user") or {}).get("url"),
                ))
        else:
            r = await c.get("https://api.pexels.com/v1/search",
                            params={"query": query, "per_page": per_page})
            r.raise_for_status()
            for p in r.json().get("photos", []):
                src = p.get("src", {})
                items.append(StockItem(
                    id=f"pexels:{p['id']}", source="pexels", kind="photo",
                    thumb=src.get("medium", src.get("small", "")),
                    download_url=src.get("large2x", src.get("large", src.get("original", ""))),
                    width=p.get("width") or 0, height=p.get("height") or 0,
                    author=p.get("photographer", ""), author_url=p.get("photographer_url"),
                ))
    return items


# -------------------------------------------------------------- Pixabay --- #
async def _pixabay(query: str, kind: str, per_page: int) -> list[StockItem]:
    key = get_settings().pixabay_api_key
    if not key:
        return []
    items: list[StockItem] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        if kind == "video":
            r = await c.get("https://pixabay.com/api/videos/",
                            params={"key": key, "q": query, "per_page": per_page})
            r.raise_for_status()
            for h in r.json().get("hits", []):
                vids = h.get("videos", {})
                pick = vids.get("medium") or vids.get("large") or vids.get("small") or {}
                if not pick.get("url"):
                    continue
                items.append(StockItem(
                    id=f"pixabay:{h['id']}", source="pixabay", kind="video",
                    thumb=(vids.get("tiny") or {}).get("thumbnail", ""),
                    download_url=pick["url"],
                    width=pick.get("width") or 0, height=pick.get("height") or 0,
                    duration=float(h.get("duration") or 0) or None,
                    author=h.get("user", ""),
                ))
        else:
            r = await c.get("https://pixabay.com/api/",
                            params={"key": key, "q": query, "image_type": "photo",
                                    "per_page": per_page})
            r.raise_for_status()
            for h in r.json().get("hits", []):
                items.append(StockItem(
                    id=f"pixabay:{h['id']}", source="pixabay", kind="photo",
                    thumb=h.get("webformatURL", h.get("previewURL", "")),
                    download_url=h.get("largeImageURL", h.get("webformatURL", "")),
                    width=h.get("imageWidth") or 0, height=h.get("imageHeight") or 0,
                    author=h.get("user", ""),
                ))
    return items


async def search(query: str, kind: str = "photo", per_page: int = 15,
                 source: str | None = None) -> list[StockItem]:
    """Recherche fusionnée sur les sources disponibles (ou une seule si `source`)."""
    kind = "video" if kind == "video" else "photo"
    results: list[StockItem] = []
    want = [source] if source else available_sources()
    for src in want:
        try:
            if src == "pexels":
                results += await _pexels(query, kind, per_page)
            elif src == "pixabay":
                results += await _pixabay(query, kind, per_page)
        except Exception:  # noqa: BLE001 — une source en panne ne casse pas la recherche
            logger.warning("Recherche stock %s échouée", src, exc_info=True)
    return results


async def download(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0), follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content
