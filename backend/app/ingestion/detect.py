"""Détection du type de document à partir de statistiques par page.

Heuristiques volontairement simples et explicables (pas de modèle ML) : elles
suffisent à router la clarification et l'animation vers le bon profil.
On pourra les remplacer par un classifieur plus tard sans toucher au reste.
"""
from __future__ import annotations

import re

from .schema import DocType, Document, DocumentPage

# Mots-clés typiques d'un article scientifique (fr + en).
_SCI_HINTS = re.compile(
    r"\b(abstract|résumé|introduction|methodology|méthodologie|references|"
    r"références|doi|et al\.|hypothesis|hypothèse)\b",
    re.IGNORECASE,
)


def page_looks_like_comic(page: DocumentPage) -> bool:
    """Une planche de BD : grande couverture d'images, très peu de texte."""
    return page.image_area_ratio >= 0.55 and page.word_count <= 60


def _landscape_ratio(pages: list[DocumentPage]) -> float:
    if not pages:
        return 0.0
    land = sum(1 for p in pages if p.width and p.height and p.width > p.height)
    return land / len(pages)


def detect_doc_type(doc: Document) -> tuple[DocType, float]:
    """Renvoie (type, confiance 0..1)."""
    pages = doc.pages
    if not pages:
        return DocType.MIXED, 0.0

    n = len(pages)
    comic_pages = sum(1 for p in pages if page_looks_like_comic(p))
    comic_frac = comic_pages / n
    avg_words = doc.total_words / n
    avg_img_ratio = doc.avg_image_area_ratio
    landscape = _landscape_ratio(pages)
    full_text = " ".join(p.text for p in pages[:5])
    sci_hits = len(_SCI_HINTS.findall(full_text))

    # 1) BD / manga : majorité de planches image-heavy.
    if comic_frac >= 0.5 or (avg_img_ratio >= 0.5 and avg_words < 80):
        conf = min(1.0, 0.5 + comic_frac / 2)
        return DocType.COMIC, conf

    # 2) Article scientifique : signaux lexicaux forts, texte dense, portrait.
    if sci_hits >= 3 and avg_words > 150 and landscape < 0.3:
        return DocType.SCIENTIFIC, min(1.0, 0.5 + sci_hits * 0.1)

    # 3) Slides / deck : pages paysage, peu de mots par page.
    if landscape >= 0.6 and avg_words < 120:
        return DocType.SLIDES, 0.7

    # 4) Rapport : texte dense.
    if avg_words >= 120:
        return DocType.REPORT, 0.7

    return DocType.MIXED, 0.4
