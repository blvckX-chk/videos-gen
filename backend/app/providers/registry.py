"""Registre central des providers disponibles."""
from __future__ import annotations

from .base import VideoProvider
from .demo import DemoProvider
from .fal import FalProvider
from .replicate import ReplicateProvider

# Ordre = ordre d'affichage dans l'UI.
_PROVIDERS: dict[str, VideoProvider] = {
    p.id: p
    for p in (
        FalProvider(),
        ReplicateProvider(),
        DemoProvider(),
    )
}


def all_providers() -> list[VideoProvider]:
    return list(_PROVIDERS.values())


def get_provider(provider_id: str) -> VideoProvider | None:
    return _PROVIDERS.get(provider_id)
