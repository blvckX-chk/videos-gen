"""Registre des providers de génération d'image (Pollinations + fal + ...).

Ordre = ordre d'affichage. Le premier disponible sert de défaut côté service.
"""
from __future__ import annotations

from .base import ImageProvider
from .fal_image import FalImageProvider
from .pollinations import PollinationsProvider

_PROVIDERS: dict[str, ImageProvider] = {
    p.id: p for p in (
        PollinationsProvider(),   # défaut gratuit sans clé
        FalImageProvider(),        # si FAL_KEY présent
    )
}


def all_image_providers() -> list[ImageProvider]:
    return list(_PROVIDERS.values())


def get_image_provider(pid: str) -> ImageProvider | None:
    return _PROVIDERS.get(pid)


def default_image_provider() -> ImageProvider:
    for p in _PROVIDERS.values():
        if p.is_available() and p.free:
            return p
    for p in _PROVIDERS.values():
        if p.is_available():
            return p
    raise RuntimeError("Aucun provider d'image disponible.")
