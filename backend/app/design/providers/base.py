"""Contrat commun aux providers de génération d'images.

Miroir de `providers/base.py` (module vidéo). Ajouter un provider = créer
une sous-classe et l'enregistrer dans `registry.py`. Le respect du champ
`tier` du blueprint v1.1 est enforced ici : un provider marqué `free=False`
ne doit être utilisé que sur un job PREMIUM.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image
from pydantic import BaseModel


class ImageProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    free: bool
    requires_key: str | None = None
    models: list[str] = []


class ImageProvider(ABC):
    id: str = "base"
    name: str = "Base"
    description: str = ""
    free: bool = False
    requires_key: str | None = None
    models: list[str] = []

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        model: str | None = None,
        seed: int | None = None,
    ) -> Image.Image:
        """Renvoie une image PIL aux dimensions demandées (ou proches)."""

    def info(self) -> ImageProviderInfo:
        return ImageProviderInfo(
            id=self.id, name=self.name, description=self.description,
            available=self.is_available(), free=self.free,
            requires_key=self.requires_key, models=self.models,
        )
