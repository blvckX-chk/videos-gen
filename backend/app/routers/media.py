"""Routes de la médiathèque : upload (rushes inclus), liste, suppression."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..media import service as svc
from ..media import storage as store
from ..media.schema import MediaItem

router = APIRouter(prefix="/api/media")

#: Les rushes vidéo sont volumineux — plafond large, mais borné.
MAX_UPLOAD_BYTES = 1024 * 1024 * 1024          # 1 Go


@router.get("", response_model=list[MediaItem])
async def list_media(kind: str | None = None) -> list[MediaItem]:
    """Tous les médias, ou seulement `photo` / `video` / `audio`."""
    return store.list_items(kind)


@router.get("/{media_id}", response_model=MediaItem)
async def media_detail(media_id: str) -> MediaItem:
    m = store.get(media_id)
    if m is None:
        raise HTTPException(404, "Média introuvable.")
    return m


@router.post("/upload", response_model=MediaItem)
async def upload(file: UploadFile = File(...),
                 name: str | None = Form(None)) -> MediaItem:
    """Importe une photo, un **rush vidéo** ou un audio dans la médiathèque."""
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Fichier vide.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Fichier trop volumineux (max 1 Go).")
    try:
        return svc.import_bytes(raw, name or (file.filename or "média"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.delete("/{media_id}")
async def media_delete(media_id: str) -> dict:
    if not store.delete(media_id):
        raise HTTPException(404, "Média introuvable.")
    return {"status": "deleted"}
