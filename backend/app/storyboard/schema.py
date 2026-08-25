"""Schéma du storyboard : le plan de tournage que le rendu (Remotion) exécute.

Un même storyboard est pensé MULTI-FORMAT : il déclare les ratios cibles
(9:16 vertical prioritaire, 1:1, 16:9) et le rendu produit une variante par
ratio. Les shots référencent la source réelle (page / case de BD) pour garantir
la fidélité au document — le génératif ne sert qu'au décor (b-roll, Slice 3+).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ShotType(str, Enum):
    TITLE = "title"      # carton titre / hook d'ouverture
    TEXT = "text"        # texte animé à l'écran (point clé)
    PAGE = "page"        # une page du document en Ken Burns
    PANEL = "panel"      # une case de BD (motion comic)
    STAT = "stat"        # un chiffre clé mis en avant
    QUOTE = "quote"      # une citation / phrase forte
    OUTRO = "outro"      # carton de fin / call to action
    BROLL = "broll"      # décor génératif IA (branché au Slice 3)


class Shot(BaseModel):
    index: int
    type: ShotType
    duration: float = 3.0                 # secondes
    text: Optional[str] = None            # texte affiché à l'écran
    narration: Optional[str] = None       # texte de voix off (Slice 4)
    source_page: Optional[int] = None     # index de page source
    source_panel: Optional[int] = None    # index de case (BD)
    transition_in: str = "fade"           # fade | slide | cut | zoom
    emphasis: Optional[str] = None        # mot/segment à souligner
    broll_prompt: Optional[str] = None    # prompt décor (Slice 3)


class Scene(BaseModel):
    index: int
    title: Optional[str] = None
    shots: list[Shot] = []

    @property
    def duration(self) -> float:
        return sum(s.duration for s in self.shots)


class Storyboard(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    document_id: str
    fps: int = 30
    #: ratios cibles ; le premier est le format principal (vertical par défaut)
    formats: list[str] = ["9:16", "1:1", "16:9"]
    #: nom du template visuel à appliquer au rendu (par pôle / secteur)
    template: str = "default"
    language: str = "fr"
    scenes: list[Scene] = []
    generator: str = "rule_based"         # rule_based | anthropic | openai

    @property
    def total_duration(self) -> float:
        return round(sum(sc.duration for sc in self.scenes), 2)

    @property
    def shot_count(self) -> int:
        return sum(len(sc.shots) for sc in self.scenes)
