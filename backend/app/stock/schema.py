"""Schémas du module Stock (banques de médias libres : Pexels, Pixabay)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class StockItem(BaseModel):
    """Un résultat de recherche (photo ou vidéo) renvoyé au front pour aperçu."""
    id: str                      # préfixé par la source, ex: "pexels:12345"
    source: str                  # pexels | pixabay
    kind: str                    # photo | video
    thumb: str                   # URL distante d'aperçu (affichée dans la grille)
    download_url: str            # URL du fichier réel à importer
    width: int = 0
    height: int = 0
    duration: Optional[float] = None   # vidéos
    author: str = ""
    author_url: Optional[str] = None


class StockClip(BaseModel):
    """Vidéo stock importée et stockée localement (servie sous /stock)."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    source: str
    kind: str = "video"
    url: str                     # /stock/<id>.mp4
    width: int = 0
    height: int = 0
    duration: Optional[float] = None
    author: str = ""
    query: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
