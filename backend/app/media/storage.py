"""Stockage de la médiathèque : fichiers sous storage/media, index persisté."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from .. import db
from ..render.assets import storage_root
from .schema import MediaItem

logger = logging.getLogger("videos_gen.media")

_COLLECTION = "media"
_ITEMS: dict[str, MediaItem] = {}

PHOTO_EXT = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXT = {"mp4", "mov", "m4v", "webm", "mkv", "avi"}
AUDIO_EXT = {"mp3", "wav", "m4a", "aac", "ogg", "flac"}


def media_dir() -> Path:
    d = storage_root() / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def media_path(media_id: str, ext: str) -> Path:
    return media_dir() / f"{media_id}.{ext}"


def probe(path: Path) -> dict:
    """Métadonnées via ffprobe : width, height, duration, fps.

    Tolérant : une sonde qui échoue renvoie des valeurs neutres plutôt que de
    faire planter l'import (un média sans métadonnées reste utilisable)."""
    out = {"width": 0, "height": 0, "duration": None, "fps": None}
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, check=False, timeout=30,
        )
        data = json.loads(r.stdout or "{}")
    except Exception:  # noqa: BLE001
        logger.warning("ffprobe a échoué sur %s", path, exc_info=True)
        return out

    dur = (data.get("format") or {}).get("duration")
    if dur:
        try:
            out["duration"] = float(dur)
        except ValueError:
            pass

    for st in data.get("streams", []):
        if st.get("codec_type") == "video":
            out["width"] = int(st.get("width") or 0)
            out["height"] = int(st.get("height") or 0)
            # avg_frame_rate est une fraction "30000/1001"
            rate = st.get("avg_frame_rate") or st.get("r_frame_rate") or ""
            if "/" in rate:
                num, _, den = rate.partition("/")
                try:
                    if float(den):
                        out["fps"] = round(float(num) / float(den), 3)
                except ValueError:
                    pass
            break
    return out


def save(item: MediaItem) -> MediaItem:
    _ITEMS[item.id] = item
    db.put(_COLLECTION, item.id, item.model_dump(mode="json"))
    return item


def get(media_id: str) -> MediaItem | None:
    return _ITEMS.get(media_id)


def list_items(kind: str | None = None) -> list[MediaItem]:
    items = sorted(_ITEMS.values(), key=lambda m: m.created_at, reverse=True)
    return [m for m in items if kind is None or m.kind.value == kind]


def delete(media_id: str) -> bool:
    item = _ITEMS.pop(media_id, None)
    if item is None:
        return False
    db.delete(_COLLECTION, media_id)
    p = media_path(media_id, item.ext)
    if p.exists():
        p.unlink()
    thumb = media_dir() / f"{media_id}.thumb.jpg"
    if thumb.exists():
        thumb.unlink()
    return True


def rehydrate() -> int:
    _ITEMS.clear()
    for data in db.all(_COLLECTION):
        try:
            m = MediaItem.model_validate(data)
            _ITEMS[m.id] = m
        except Exception:  # noqa: BLE001
            logger.warning("Média illisible ignoré", exc_info=True)
    return len(_ITEMS)
