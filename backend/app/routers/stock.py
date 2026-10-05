"""Routes du module Stock : recherche et import de médias libres."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..stock import service, storage
from ..stock.schema import StockClip, StockItem

router = APIRouter(prefix="/api/stock")


@router.get("/sources")
async def sources() -> dict:
    """Sources disponibles (selon les clés configurées)."""
    return {"sources": service.available_sources()}


@router.get("/search", response_model=list[StockItem])
async def search(q: str, kind: str = "photo", per_page: int = 15,
                 source: str | None = None) -> list[StockItem]:
    if not q.strip():
        return []
    if not service.available_sources():
        raise HTTPException(503, "Aucune banque configurée : ajoute PEXELS_API_KEY "
                                 "ou PIXABAY_API_KEY dans backend/.env.")
    return await service.search(q.strip(), kind=kind, per_page=per_page, source=source)


@router.get("/clips", response_model=list[StockClip])
async def clips() -> list[StockClip]:
    return storage.list_clips()


class ImportRequest(BaseModel):
    item: StockItem
    query: str = ""


@router.post("/import")
async def import_item(req: ImportRequest) -> dict:
    """Télécharge le média choisi et le range (photo → bibliothèque, vidéo → /stock)."""
    try:
        raw = await service.download(req.item.download_url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Téléchargement impossible : {exc}") from exc

    if req.item.kind == "video":
        clip = await storage.import_video(req.item, raw, req.query)
        return {"kind": "video", "clip": clip.model_dump(mode="json")}
    asset = await storage.import_photo(req.item, raw)
    return {"kind": "photo", "asset": asset.model_dump(mode="json")}
