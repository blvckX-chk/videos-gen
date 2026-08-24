"""Extracteur par défaut basé sur PyMuPDF (fitz).

Léger (pas de GPU, pas de modèle), rapide, offline — idéal pour le Slice 1.
Il fournit texte + statistiques d'images par page, ce qui suffit à la détection
de type et à la clarification. Pour des tableaux/figures complexes ou des
panneaux de BD, on branchera plus tard Docling / un extracteur dédié.
"""
from __future__ import annotations

import re

from .base import Extractor
from .detect import detect_doc_type, page_looks_like_comic
from .schema import Document, DocumentPage

try:  # PyMuPDF est optionnel à l'import pour ne pas casser si absent.
    import fitz  # type: ignore
    _HAS_FITZ = True
except Exception:  # pragma: no cover
    _HAS_FITZ = False


def _guess_language(text: str) -> str | None:
    if not text.strip():
        return None
    t = f" {text.lower()} "
    fr = sum(t.count(w) for w in (" le ", " la ", " les ", " des ", " est ", " une ", " et ", " à "))
    en = sum(t.count(w) for w in (" the ", " and ", " is ", " of ", " to ", " a ", " in ", " for "))
    if fr == en == 0:
        return None
    return "fr" if fr >= en else "en"


class PyMuPDFExtractor(Extractor):
    id = "pymupdf"
    name = "PyMuPDF"

    def is_available(self) -> bool:
        return _HAS_FITZ

    def extract(self, data: bytes, filename: str) -> Document:
        if not _HAS_FITZ:
            raise RuntimeError("PyMuPDF non installé (pip install PyMuPDF).")

        pdf = fitz.open(stream=data, filetype="pdf")
        pages: list[DocumentPage] = []
        total_chars = total_words = total_images = 0
        img_ratio_sum = 0.0

        for i, page in enumerate(pdf):
            rect = page.rect
            page_area = float(rect.width * rect.height) or 1.0
            text = page.get_text("text") or ""
            words = len(text.split())

            # Surface couverte par les images (union approximée par somme bornée).
            img_area = 0.0
            image_count = 0
            for img in page.get_images(full=True):
                image_count += 1
                try:
                    for r in page.get_image_rects(img[0]):
                        img_area += float(r.width * r.height)
                except Exception:
                    pass
            image_area_ratio = max(0.0, min(1.0, img_area / page_area))

            dp = DocumentPage(
                index=i,
                text=text.strip(),
                char_count=len(text),
                word_count=words,
                image_count=image_count,
                image_area_ratio=round(image_area_ratio, 3),
                width=float(rect.width),
                height=float(rect.height),
            )
            dp.looks_like_comic_page = page_looks_like_comic(dp)
            pages.append(dp)

            total_chars += dp.char_count
            total_words += dp.word_count
            total_images += dp.image_count
            img_ratio_sum += image_area_ratio

        n = len(pages) or 1
        doc = Document(
            filename=filename,
            page_count=len(pages),
            total_chars=total_chars,
            total_words=total_words,
            total_images=total_images,
            avg_image_area_ratio=round(img_ratio_sum / n, 3),
            pages=pages,
        )

        # Titre probable : métadonnée PDF, sinon première ligne non vide.
        meta_title = (pdf.metadata or {}).get("title") if pdf.metadata else None
        if meta_title and meta_title.strip():
            doc.title_guess = meta_title.strip()
        elif pages and pages[0].text:
            first_line = next((l.strip() for l in pages[0].text.splitlines() if l.strip()), None)
            doc.title_guess = (first_line[:120] if first_line else None)

        doc.language_guess = _guess_language(" ".join(p.text for p in pages[:3]))
        doc.doc_type, doc.doc_type_confidence = detect_doc_type(doc)

        pdf.close()
        return doc
