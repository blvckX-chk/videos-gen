"""Schémas du tri et de la curation de photos."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PhotoAnalysis(BaseModel):
    """Mesures objectives d'une photo (couche déterministe, sans IA)."""
    media_id: str
    sharpness: float = 0.0        # variance du Laplacien (plus haut = plus net)
    brightness: float = 0.0       # luminance moyenne 0-255
    clipped: float = 0.0          # part de pixels bouchés ou cramés (0-1)
    faces: int = 0
    score: float = 0.0            # note de synthèse 0-100
    issues: list[str] = []        # "flou", "sombre", "surexposé", "doublon"
    #: id de la photo retenue du groupe quand celle-ci est un quasi-doublon
    duplicate_of: Optional[str] = None
    keep: bool = True             # recommandation de la couche déterministe


class ScenarioClip(BaseModel):
    """Un plan proposé par le scénario."""
    media_id: str
    duration: float = 2.5
    text: Optional[str] = None
    ken_burns: bool = True


class Scenario(BaseModel):
    """Proposition de montage : sélection + ordre narratif."""
    title: str = "Montage"
    #: comment la sélection a été faite (déterministe seul, ou curation IA)
    engine: str = "rule_based"
    rationale: str = ""
    clips: list[ScenarioClip] = []
    #: photos écartées, avec la raison (transparence pour l'utilisateur)
    rejected: list[PhotoAnalysis] = []
