"""Store en mémoire des documents ingérés (MVP).

On conserve aussi les octets bruts du PDF pour permettre un retraitement
ultérieur (ex: segmentation des cases de BD à la demande).

Pour la production : remplacer par une base + stockage objet (les PDF peuvent
être volumineux et sensibles → prévoir chiffrement/rétention)."""
from __future__ import annotations

from ..ingestion.schema import Document

_DOCS: dict[str, Document] = {}
_BYTES: dict[str, bytes] = {}


def save_document(doc: Document, raw: bytes | None = None) -> Document:
    _DOCS[doc.id] = doc
    if raw is not None:
        _BYTES[doc.id] = raw
    return doc


def get_document(doc_id: str) -> Document | None:
    return _DOCS.get(doc_id)


def get_document_bytes(doc_id: str) -> bytes | None:
    return _BYTES.get(doc_id)


def list_documents(limit: int = 50) -> list[Document]:
    docs = sorted(_DOCS.values(), key=lambda d: d.created_at, reverse=True)
    return docs[:limit]
