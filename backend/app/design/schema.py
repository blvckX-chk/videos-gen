"""Schémas du module Graphic Design.

Un `DesignAsset` = un visuel statique manipulable (généré, uploadé ou dérivé).
Un `DesignJob` = une opération asynchrone (génération, retrait de fond, upscale).
Un `Composition` = spec déclarative pour composer plusieurs couches en un final.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AssetKind(str, Enum):
    GENERATED = "generated"        # sortie d'un provider d'image
    UPLOADED = "uploaded"          # image uploadée par l'utilisateur
    PROCESSED = "processed"        # dérivée d'une image (bg removed, resized...)
    COMPOSED = "composed"          # sortie d'une composition (multi-couches)


class ImageFormat(str, Enum):
    """Formats livrés d'emblée pour le CM social."""
    SQUARE = "square"              # 1080×1080 · post IG/FB
    STORY = "story"                # 1080×1920 · story / reel cover
    LANDSCAPE = "landscape"        # 1280×720  · thumbnail YouTube
    LARGE_SQUARE = "large_square"  # 2048×2048 · print / retail
    A4 = "a4"                      # 2480×3508 · impression (à 300 DPI)


FORMAT_DIMS: dict[str, tuple[int, int]] = {
    ImageFormat.SQUARE: (1080, 1080),
    ImageFormat.STORY: (1080, 1920),
    ImageFormat.LANDSCAPE: (1280, 720),
    ImageFormat.LARGE_SQUARE: (2048, 2048),
    ImageFormat.A4: (2480, 3508),
}


class DesignAsset(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    kind: AssetKind
    url: str                          # relative, ex: /design/<id>.png
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    #: généalogie (id du parent pour les dérivés)
    parent_id: Optional[str] = None
    #: provider utilisé (pour la traçabilité coût / v1.1 tier)
    provider: Optional[str] = None
    #: prompt éventuel (générations)
    prompt: Optional[str] = None
    format: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DesignJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DesignJob(BaseModel):
    """Job asynchrone d'une opération design (async pour ne pas bloquer l'HTTP)."""
    id: str = Field(default_factory=lambda: uuid4().hex)
    kind: str                         # "generate" | "remove_bg" | "compose" | "resize" | ...
    status: DesignJobStatus = DesignJobStatus.QUEUED
    output_asset_ids: list[str] = []
    error: Optional[str] = None
    #: coût estimé de l'opération, en centimes (0 pour le tier free)
    cost_cents: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Composition déclarative — la vraie richesse du toolkit.
# On empile des LAYERS dans l'ordre (background → foreground).
# --------------------------------------------------------------------------- #
class Anchor(str, Enum):
    TOP_LEFT = "top_left"; TOP = "top"; TOP_RIGHT = "top_right"
    LEFT = "left"; CENTER = "center"; RIGHT = "right"
    BOTTOM_LEFT = "bottom_left"; BOTTOM = "bottom"; BOTTOM_RIGHT = "bottom_right"


class LayerType(str, Enum):
    SOLID = "solid"          # aplat de couleur
    GRADIENT = "gradient"    # dégradé linéaire
    IMAGE = "image"          # image (asset_id d'un asset existant, OU url http)
    TEXT = "text"            # texte
    SHAPE = "shape"          # forme (rectangle / cercle) — utilitaire


class Layer(BaseModel):
    type: LayerType
    #: opacité 0..1
    opacity: float = 1.0
    anchor: Anchor = Anchor.CENTER
    #: offset relatif au canvas (px) après ancrage
    dx: int = 0
    dy: int = 0
    #: dimensions cible (px). None = auto (image = taille source, texte = wrap).
    width: Optional[int] = None
    height: Optional[int] = None
    #: SOLID / GRADIENT
    color: Optional[str] = None
    color2: Optional[str] = None
    gradient_angle: float = 90.0
    #: IMAGE
    asset_id: Optional[str] = None
    asset_url: Optional[str] = None
    fit: str = "cover"                       # cover | contain | stretch
    corner_radius: int = 0
    #: TEXT
    text: Optional[str] = None
    font_size: int = 64
    font_weight: str = "bold"                # regular | bold
    text_color: str = "#FFFFFF"
    text_align: str = "left"                 # left | center | right
    max_width: Optional[int] = None
    line_height: float = 1.1
    letter_spacing: float = 0.0
    stroke_color: Optional[str] = None
    stroke_width: int = 0
    shadow: bool = False
    #: SHAPE
    shape: str = "rect"                      # rect | circle
    fill: Optional[str] = None
    stroke: Optional[str] = None


class Composition(BaseModel):
    """Spec déclarative d'un visuel composé — sérialisable, versionnable,
    réutilisable comme template."""
    name: str = "sans nom"
    format: ImageFormat = ImageFormat.SQUARE
    width: Optional[int] = None              # override du format
    height: Optional[int] = None
    background: str = "#0B0D12"              # couleur de fond par défaut
    layers: list[Layer] = []
