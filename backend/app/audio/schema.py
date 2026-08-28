"""Schémas du module audio toolkit.

Un `AudioClip` = une piste audio réutilisable (bibliothèque). Il peut être :
  - `original`     : extrait direct d'une vidéo source
  - `vocals`       : uniquement la voix (isolée par Demucs)
  - `instrumental` : tout sauf la voix (musique/bruits — le fameux « karaoké »)
  - `custom`       : upload direct d'un fichier audio
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ClipKind(str, Enum):
    ORIGINAL = "original"
    VOCALS = "vocals"
    INSTRUMENTAL = "instrumental"
    CUSTOM = "custom"


class AudioClip(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    kind: ClipKind = ClipKind.ORIGINAL
    #: id du clip parent (si dérivé par séparation)
    parent_id: Optional[str] = None
    #: URL relative servie par le backend (ex: /audio/<id>.mp3)
    url: str
    duration_seconds: float = 0.0
    sample_rate: int = 44100
    channels: int = 2
    size_bytes: int = 0
    source_video_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AudioJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AudioJob(BaseModel):
    """Job long (séparation Demucs, remux) — polling côté client."""
    id: str = Field(default_factory=lambda: uuid4().hex)
    kind: str                             # "extract" | "separate" | "apply"
    status: AudioJobStatus = AudioJobStatus.QUEUED
    input_clip_id: Optional[str] = None
    output_clip_ids: list[str] = []       # séparation → 2 stems
    output_video_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
