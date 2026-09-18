"""Schémas du module Copywriting (pilier 360° n°2).

Produit un copy **natif par plateforme** (le ton TikTok ≠ LinkedIn ≠ pub Meta),
en variantes A/B, à partir d'un brief / document / intention.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE_SHORTS = "youtube_shorts"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    META_AD = "meta_ad"


class CopyVariant(BaseModel):
    label: str                 # "A", "B"…
    hook: str                  # accroche scroll-stop (1re ligne)
    body: str                  # corps
    cta: str                   # call to action
    hashtags: list[str] = []


class PlatformCopy(BaseModel):
    platform: Platform
    variants: list[CopyVariant] = []


class CopyRequest(BaseModel):
    intent: Optional[str] = None
    document_id: Optional[str] = None
    platforms: list[Platform] = Field(default_factory=lambda: [Platform.TIKTOK, Platform.INSTAGRAM])
    tone: Optional[str] = None
    charte_id: Optional[str] = None
    language: str = "fr"
    variants: int = 2


class CopyResult(BaseModel):
    platforms: list[PlatformCopy] = []
    generator: str = "rule_based"   # rule_based | anthropic | openai
