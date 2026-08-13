"""Contrat commun à tous les providers de génération vidéo.

Ajouter un provider = créer une sous-classe de `VideoProvider` et l'enregistrer
dans `registry.py`. Le reste de l'application n'a pas besoin de connaître les
détails de chaque API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job, ProviderInfo


class VideoProvider(ABC):
    #: identifiant unique et court, utilisé dans l'API (ex: "fal")
    id: str = "base"
    #: nom lisible
    name: str = "Base"
    #: description courte affichée dans l'UI
    description: str = ""
    #: True si utilisable gratuitement (sans carte bancaire)
    free: bool = False
    #: nom de la variable d'env requise, ou None si aucune
    requires_key: str | None = None
    #: modèles proposés (le premier est le défaut)
    models: list[str] = []

    @abstractmethod
    def is_available(self) -> bool:
        """Le provider peut-il être utilisé (clé présente, etc.) ?"""

    @abstractmethod
    async def generate(self, job: Job) -> str:
        """Lance la génération et renvoie l'URL de la vidéo finale.

        Doit être asynchrone et lever une exception en cas d'échec.
        Le `job` contient déjà le prompt (éventuellement amélioré).
        """

    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            available=self.is_available(),
            free=self.free,
            models=self.models,
            requires_key=self.requires_key,
        )
