"""Schémas du document ingéré (indépendants de l'extracteur utilisé)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class DocType(str, Enum):
    """Type de document détecté — pilote la clarification et l'animation."""
    REPORT = "report"          # texte dense (rapport, note, contrat)
    SLIDES = "slides"          # présentation / pitch deck
    SCIENTIFIC = "scientific"  # article scientifique (abstract, références)
    COMIC = "comic"            # BD / manga (cases, bulles, image-heavy)
    MIXED = "mixed"            # indéterminé / hybride


class DocumentPage(BaseModel):
    index: int
    text: str = ""
    char_count: int = 0
    word_count: int = 0
    image_count: int = 0
    #: part de la surface de la page couverte par des images (0..1)
    image_area_ratio: float = 0.0
    width: float = 0.0
    height: float = 0.0
    #: True si la page ressemble à une planche de BD (image-heavy, peu de texte)
    looks_like_comic_page: bool = False


class Panel(BaseModel):
    """Une case de BD, en coordonnées normalisées (0..1) relatives à la page."""
    index: int              # ordre de lecture dans la page
    x: float
    y: float
    w: float
    h: float
    area_ratio: float       # part de la surface de la page


class PagePanels(BaseModel):
    page_index: int
    reading_direction: str = "ltr"   # ltr (BD occidentale) | rtl (manga)
    panel_count: int = 0
    panels: list[Panel] = []
    #: miniature de la page (JPEG base64) pour dessiner les cases dans l'UI
    thumbnail: Optional[str] = None
    thumb_width: int = 0
    thumb_height: int = 0


class Document(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    filename: str
    page_count: int = 0
    doc_type: DocType = DocType.MIXED
    doc_type_confidence: float = 0.0
    title_guess: Optional[str] = None
    language_guess: Optional[str] = None
    total_chars: int = 0
    total_words: int = 0
    total_images: int = 0
    avg_image_area_ratio: float = 0.0
    pages: list[DocumentPage] = []
    #: cases détectées (BD), remplies à la demande via /documents/{id}/panels
    panels: Optional[list[PagePanels]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def summary(self, max_chars: int = 1500) -> str:
        """Résumé textuel compact du document, pour alimenter le LLM de clarification."""
        head = " ".join(p.text for p in self.pages[:3]).strip()
        head = head[:max_chars]
        return (
            f"Fichier: {self.filename}\n"
            f"Type détecté: {self.doc_type.value} (confiance {self.doc_type_confidence:.0%})\n"
            f"Pages: {self.page_count} | Mots: {self.total_words} | Images: {self.total_images}\n"
            f"Titre probable: {self.title_guess or '—'}\n"
            f"Langue probable: {self.language_guess or '—'}\n"
            f"Extrait:\n{head}"
        )
