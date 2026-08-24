"""Routes du Slice 1 : ingestion PDF + clarification."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..ingestion.panels import extract_panels
from ..ingestion.registry import get_extractor
from ..ingestion.schema import Document, PagePanels
from ..services.clarification import (
    Brief,
    ClarificationQuestion,
    build_brief,
    generate_questions,
)
from ..services.documents import (
    get_document,
    get_document_bytes,
    list_documents,
    save_document,
)

router = APIRouter(prefix="/api")

_MAX_BYTES = 40 * 1024 * 1024  # 40 Mo


class IngestResponse(BaseModel):
    document: Document
    questions: list[ClarificationQuestion]


class BriefRequest(BaseModel):
    document_id: str
    answers: dict[str, str]


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Seuls les fichiers PDF sont acceptés pour l'instant.")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide.")
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "Fichier trop volumineux (max 40 Mo).")

    try:
        extractor = get_extractor()
        doc = extractor.extract(data, file.filename)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"Échec de l'ingestion: {exc}") from exc

    save_document(doc, raw=data)
    questions = await generate_questions(doc)
    return IngestResponse(document=doc, questions=questions)


class PanelsResponse(BaseModel):
    document_id: str
    reading_direction: str
    pages: list[PagePanels]


@router.post("/documents/{doc_id}/panels", response_model=PanelsResponse)
async def detect_panels(
    doc_id: str,
    direction: str = "ltr",
    max_pages: int = 12,
    thumbnails: bool = True,
) -> PanelsResponse:
    """Segmente les cases (panels) d'une BD déjà ingérée.

    `direction` : "ltr" (BD occidentale) ou "rtl" (manga)."""
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Document introuvable — ré-ingère le PDF.")
    raw = get_document_bytes(doc_id)
    if raw is None:
        raise HTTPException(410, "Octets du PDF non disponibles — ré-ingère le PDF.")
    if direction not in {"ltr", "rtl"}:
        raise HTTPException(400, "direction doit être 'ltr' ou 'rtl'.")

    try:
        pages = extract_panels(raw, direction=direction, max_pages=max_pages,
                               with_thumbnails=thumbnails)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, f"Échec de la segmentation: {exc}") from exc

    doc.panels = pages
    return PanelsResponse(document_id=doc_id, reading_direction=direction, pages=pages)


@router.get("/documents", response_model=list[Document])
async def documents(limit: int = 50) -> list[Document]:
    return list_documents(limit)


@router.get("/documents/{doc_id}", response_model=Document)
async def document_detail(doc_id: str) -> Document:
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Document introuvable")
    return doc


@router.post("/brief", response_model=Brief)
async def make_brief(req: BriefRequest) -> Brief:
    doc = get_document(req.document_id)
    if doc is None:
        raise HTTPException(404, "Document introuvable — ré-ingère le PDF.")
    return build_brief(doc, req.answers)
