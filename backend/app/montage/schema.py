"""Modèle de montage : une Timeline = une suite de plans à assembler.

Volontairement indépendant du moteur de rendu : la même timeline peut être
rendue par FFmpeg (assemblage de clips) ou par Remotion (surcouches animées).
C'est ce découplage qui permettra d'ajouter la timeline UI sans tout refaire.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class VideoFormat(str, Enum):
    VERTICAL = "9:16"
    SQUARE = "1:1"
    LANDSCAPE = "16:9"


#: Résolutions cibles (largeur, hauteur) — 1080p de base, standard réseaux.
FORMAT_DIMS: dict[VideoFormat, tuple[int, int]] = {
    VideoFormat.VERTICAL: (1080, 1920),
    VideoFormat.SQUARE: (1080, 1080),
    VideoFormat.LANDSCAPE: (1920, 1080),
}


class Transition(str, Enum):
    CUT = "cut"          # coupe franche
    FADE = "fade"        # fondu d'ouverture sur le plan


class FitMode(str, Enum):
    """Comment un média au mauvais ratio entre dans le cadre."""
    BLUR = "blur"        # image entière sur fond flouté — rien n'est coupé (défaut)
    COVER = "cover"      # remplit en recadrant, centré sur les visages
    CONTAIN = "contain"  # conserve tout, ajoute des bandes noires


class TransitionStyle(str, Enum):
    """Enchaînement entre les plans, appliqué à tout le montage."""
    CUT = "cut"              # coupes franches (assemblage rapide, sans ré-encodage)
    DISSOLVE = "dissolve"    # fondus enchaînés (les plans se chevauchent)
    VARIED = "varied"        # transitions variées (glissements, volets, cercle)


class TimelineClip(BaseModel):
    """Un plan : un média (photo ou vidéo) placé sur la timeline."""
    media_id: str
    #: point d'entrée dans le média source (vidéo uniquement), en secondes
    in_point: float = 0.0
    #: durée du plan sur la timeline, en secondes
    duration: float = 3.0
    transition: Transition = Transition.CUT
    #: texte incrusté (titre de plan) — surcouche optionnelle
    text: Optional[str] = None
    #: léger zoom progressif (Ken Burns) — donne vie aux photos fixes
    ken_burns: bool = False


class Timeline(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = "Montage"
    format: VideoFormat = VideoFormat.VERTICAL
    fps: int = 30
    #: remplir le cadre (recadrage) plutôt que des bandes noires
    fit_mode: FitMode = FitMode.BLUR
    #: enchaînement entre plans, appliqué à l'ensemble du montage
    transition_style: TransitionStyle = TransitionStyle.VARIED
    clips: list[TimelineClip] = []
    #: piste son : musique de fond (média audio de la médiathèque)
    music_media_id: Optional[str] = None
    #: narration : texte lu en voix off (synthétisé au rendu)
    narration: Optional[str] = None
    #: filigrane décidé côté serveur selon le rôle (jamais par le client)
    role: Optional[str] = None
    charte_id: Optional[str] = None
    remove_watermark: bool = False
    watermark_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_duration(self) -> float:
        return round(sum(c.duration for c in self.clips), 3)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class MontageJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class MontageJob(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    timeline_id: str
    status: MontageJobStatus = MontageJobStatus.QUEUED
    #: étape courante, pour un retour lisible côté UI
    step: str = ""
    clips_total: int = 0
    clips_done: int = 0
    video_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
