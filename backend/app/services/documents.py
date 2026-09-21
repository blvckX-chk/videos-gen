"""Store des documents ingérés : cache mémoire + persistance.

- Les **métadonnées** (schéma `Document`) vont en base via `db` (collection
  `documents`) et sont réhydratées au démarrage.
- Les **octets bruts** du PDF (potentiellement volumineux) vont sur disque
  dans `storage/uploads/<id>.pdf` — conservés pour un retraitement ultérieur
  (ex : segmentation des cases de BD à la demande).

Production : stockage objet chiffré + rétention pour les PDF sensibles."""
from __future__ import annotations

import logging

from .. import db
from ..ingestion.schema import Document

logger = logging.getLogger("videos_gen.documents")

_COLLECTION = "documents"
_DOCS: dict[str, Document] = {}


def uploads_dir():
    # Import différé : render.assets importe ce module (get_document_bytes) →
    # éviter l'import circulaire au chargement.
    from ..render.assets import storage_root

    d = storage_root() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _bytes_path(doc_id: str):
    return uploads_dir() / f"{doc_id}.pdf"


def save_document(doc: Document, raw: bytes | None = None) -> Document:
    _DOCS[doc.id] = doc
    db.put(_COLLECTION, doc.id, doc.model_dump(mode="json"))
    if raw is not None:
        _bytes_path(doc.id).write_bytes(raw)
    return doc


def get_document(doc_id: str) -> Document | None:
    return _DOCS.get(doc_id)


def get_document_bytes(doc_id: str) -> bytes | None:
    p = _bytes_path(doc_id)
    return p.read_bytes() if p.exists() else None


def list_documents(limit: int = 50) -> list[Document]:
    docs = sorted(_DOCS.values(), key=lambda d: d.created_at, reverse=True)
    return docs[:limit]


def rehydrate() -> int:
    """Recharge les métadonnées documents depuis la base (au démarrage)."""
    _DOCS.clear()
    for data in db.all(_COLLECTION):
        try:
            doc = Document.model_validate(data)
            _DOCS[doc.id] = doc
        except Exception:  # noqa: BLE001
            logger.warning("Document illisible ignoré à la réhydratation", exc_info=True)
    return len(_DOCS)
