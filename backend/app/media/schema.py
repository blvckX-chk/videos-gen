"""Médiathèque unifiée — un seul modèle pour photos, vidéos (rushes) et audio.

Avant, les médias étaient éclatés (assets design / clips audio / clips stock) et
les rushes vidéo n'avaient nulle part où aller : impossible de monter. Ici tout
média utilisable dans un montage porte les mêmes métadonnées.

`license` / `author` ne sont pas décoratifs : l'attribution est une obligation
des banques libres (Pexels, Pixabay) — on la trace dès l'entrée.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MediaKind(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"


class MediaItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    kind: MediaKind
    name: str
    ext: str                                   # mp4, jpg, mp3…
    url: str                                   # /media/<id>.<ext>
    width: int = 0
    height: int = 0
    duration: Optional[float] = None           # secondes (vidéo / audio)
    fps: Optional[float] = None                # vidéo
    size_bytes: int = 0
    #: provenance : upload | stock:pexels | stock:pixabay | design | tchavi:<modèle>
    source: str = "upload"
    author: Optional[str] = None
    license: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_timeline_usable(self) -> bool:
        """Photo et vidéo peuvent devenir un plan ; l'audio sert de piste son."""
        return self.kind in (MediaKind.PHOTO, MediaKind.VIDEO)
