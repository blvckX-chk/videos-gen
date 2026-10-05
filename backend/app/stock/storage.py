"""Stockage des clips vidéo stock importés (persistés) + import des médias.

Photos importées → bibliothèque Design (réutilise design.storage) pour être
directement composables. Vidéos → storage/stock/<id>.mp4, servi sous /stock.
"""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from .. import db
from ..render.assets import storage_root
from .schema import StockClip

logger = logging.getLogger("videos_gen.stock")

_COLLECTION = "stock_clips"
_CLIPS: dict[str, StockClip] = {}


def stock_dir() -> Path:
    d = storage_root() / "stock"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_clip(clip: StockClip) -> StockClip:
    _CLIPS[clip.id] = clip
    db.put(_COLLECTION, clip.id, clip.model_dump(mode="json"))
    return clip


def list_clips() -> list[StockClip]:
    return sorted(_CLIPS.values(), key=lambda c: c.created_at, reverse=True)


def rehydrate() -> int:
    _CLIPS.clear()
    for data in db.all(_COLLECTION):
        try:
            c = StockClip.model_validate(data)
            _CLIPS[c.id] = c
        except Exception:  # noqa: BLE001
            logger.warning("Clip stock illisible ignoré", exc_info=True)
    return len(_CLIPS)


async def import_photo(item, raw: bytes):
    """Enregistre une photo stock dans la bibliothèque Design."""
    from ..design.schema import AssetKind, DesignAsset
    from ..design.storage import asset_path, save_asset

    asset_id = uuid4().hex
    path = asset_path(asset_id, "jpg")
    path.write_bytes(raw)
    asset = DesignAsset(
        id=asset_id, name=f"stock · {item.source}", kind=AssetKind.UPLOADED,
        url=f"/design/{asset_id}.jpg", width=item.width, height=item.height,
        size_bytes=len(raw), provider=f"stock:{item.source}",
    )
    return save_asset(asset)


async def import_video(item, raw: bytes, query: str = "") -> StockClip:
    """Enregistre une vidéo stock localement et la référence."""
    clip = StockClip(source=item.source, width=item.width, height=item.height,
                     duration=item.duration, author=item.author, query=query,
                     url="")
    path = stock_dir() / f"{clip.id}.mp4"
    path.write_bytes(raw)
    clip.url = f"/stock/{clip.id}.mp4"
    return save_clip(clip)
