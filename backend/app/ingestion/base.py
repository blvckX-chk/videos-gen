"""Contrat commun aux extracteurs de documents.

Ajouter un extracteur (ex: Docling pour de meilleurs tableaux, un extracteur
« panels BD » pour les bandes dessinées) = créer une sous-classe et l'enregistrer.
Le reste du pipeline ne dépend que du schéma `Document`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .schema import Document


class Extractor(ABC):
    id: str = "base"
    name: str = "Base"

    @abstractmethod
    def is_available(self) -> bool:
        """Les dépendances de cet extracteur sont-elles présentes ?"""

    @abstractmethod
    def extract(self, data: bytes, filename: str) -> Document:
        """Transforme des octets de PDF en `Document` structuré."""
