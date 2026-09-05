"""Contrat commun aux providers de synthèse vocale (TTS).

Miroir des autres registries. `free=True` = utilisable sur le tier gratuit
(garde-fou blueprint v1.1). Chaque provider écrit un fichier audio (WAV ou MP3)
et renvoie son chemin.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel


class TTSProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    free: bool
    requires_key: str | None = None
    voices: list[str] = []


class TTSProvider(ABC):
    id: str = "base"
    name: str = "Base"
    description: str = ""
    free: bool = False
    requires_key: str | None = None
    voices: list[str] = []

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def synthesize(self, text: str, out_path: Path,
                         voice: str | None = None, lang: str = "fr") -> Path:
        """Synthétise `text` dans `out_path`. Renvoie le chemin écrit."""

    def info(self) -> TTSProviderInfo:
        return TTSProviderInfo(
            id=self.id, name=self.name, description=self.description,
            available=self.is_available(), free=self.free,
            requires_key=self.requires_key, voices=self.voices,
        )
