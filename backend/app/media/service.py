"""Import de médias dans la médiathèque (upload, ou reprise d'un fichier local)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .schema import MediaItem, MediaKind
from .storage import (
    AUDIO_EXT,
    PHOTO_EXT,
    VIDEO_EXT,
    media_path,
    probe,
    save,
)


def kind_for_ext(ext: str) -> MediaKind | None:
    ext = ext.lower().lstrip(".")
    if ext in PHOTO_EXT:
        return MediaKind.PHOTO
    if ext in VIDEO_EXT:
        return MediaKind.VIDEO
    if ext in AUDIO_EXT:
        return MediaKind.AUDIO
    return None


def _make_video_thumb(src: Path, dest: Path, at: float) -> bool:
    """Extrait une image d'aperçu de la vidéo (sans quoi la médiathèque
    n'afficherait que des noms de fichiers)."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{at:.2f}", "-i", str(src),
             "-frames:v", "1", "-vf", "scale=480:-2", str(dest)],
            capture_output=True, check=False, timeout=60,
        )
        return r.returncode == 0 and dest.exists()
    except Exception:  # noqa: BLE001 — une vignette manquante n'est pas bloquante
        return False


def _finalize(item: MediaItem, path: Path) -> MediaItem:
    """Complète les métadonnées après écriture du fichier."""
    info = probe(path)
    item.width = info["width"]
    item.height = info["height"]
    item.duration = info["duration"]
    item.fps = info["fps"]
    item.size_bytes = path.stat().st_size
    item.url = f"/media/{item.id}.{item.ext}"

    if item.kind == MediaKind.PHOTO:
        item.thumb_url = item.url
    elif item.kind == MediaKind.VIDEO:
        thumb = path.parent / f"{item.id}.thumb.jpg"
        # 1 s dans le plan, ou le tout début si la vidéo est plus courte
        at = 1.0 if (item.duration or 0) > 1.2 else 0.0
        if _make_video_thumb(path, thumb, at):
            item.thumb_url = f"/media/{thumb.name}"
    return save(item)


def import_bytes(raw: bytes, filename: str, *, source: str = "upload",
                 author: str | None = None, license: str | None = None) -> MediaItem:
    """Range un fichier uploadé (photo, rush vidéo ou audio) dans la médiathèque."""
    ext = (Path(filename).suffix or "").lower().lstrip(".") or "bin"
    kind = kind_for_ext(ext)
    if kind is None:
        raise ValueError(f"Format non pris en charge : .{ext}")
    item = MediaItem(kind=kind, name=Path(filename).stem or "média", ext=ext,
                     url="", source=source, author=author, license=license)
    path = media_path(item.id, ext)
    path.write_bytes(raw)
    return _finalize(item, path)


def import_file(src: Path, *, name: str | None = None, source: str = "upload",
                author: str | None = None, license: str | None = None) -> MediaItem:
    """Reprend un fichier déjà présent sur le disque (stock importé, rendu…)."""
    ext = src.suffix.lower().lstrip(".") or "bin"
    kind = kind_for_ext(ext)
    if kind is None:
        raise ValueError(f"Format non pris en charge : .{ext}")
    item = MediaItem(kind=kind, name=name or src.stem, ext=ext, url="",
                     source=source, author=author, license=license)
    dest = media_path(item.id, ext)
    shutil.copy2(src, dest)
    return _finalize(item, dest)
