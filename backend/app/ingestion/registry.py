"""Sélection de l'extracteur à utiliser.

Ordre de préférence ; on prend le premier disponible. Ajouter Docling ou un
extracteur BD (détection de cases) ici, avant PyMuPDF, quand ils seront prêts.
"""
from __future__ import annotations

from .base import Extractor
from .pymupdf_extractor import PyMuPDFExtractor

_EXTRACTORS: list[Extractor] = [
    # DoclingExtractor(),        # ← à ajouter (tableaux/figures)
    # ComicPanelExtractor(),     # ← à ajouter (cases + bulles BD)
    PyMuPDFExtractor(),
]


def get_extractor() -> Extractor:
    for ex in _EXTRACTORS:
        if ex.is_available():
            return ex
    raise RuntimeError("Aucun extracteur disponible (installe PyMuPDF).")
