"""Store en mémoire des documents ingérés (MVP).

Pour la production : remplacer par une base + stockage objet (les PDF peuvent
être volumineux et sensibles → prévoir chiffrement/rétention)."""
from __future__ import annotations

from ..ingestion.schema import Document

_DOCS: dict[str, Document] = {}


def save_document(doc: Document) -> Document:
    _DOCS[doc.id] = doc
    return doc


def get_document(doc_id: str) -> Document | None:
    return _DOCS.get(doc_id)


def list_documents(limit: int = 50) -> list[Document]:
    docs = sorted(_DOCS.values(), key=lambda d: d.created_at, reverse=True)
    return docs[:limit]
