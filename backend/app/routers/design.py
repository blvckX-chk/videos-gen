"""Routes du module Graphic Design."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..design import service as svc
from ..design.processing import rembg_available
from ..design.providers.base import ImageProviderInfo
from ..design.providers.registry import all_image_providers
from ..design.schema import (
    Composition,
    DesignAsset,
    DesignJob,
    DesignJobStatus,
    FORMAT_DIMS,
    ImageFormat,
)
from ..design.storage import delete_asset, get_asset, get_job, list_assets, save_job
from ..models import Tier

router = APIRouter(prefix="/api/design")


class ToolkitInfo(BaseModel):
    formats: dict[str, tuple[int, int]]
    rembg_available: bool
    providers: list[ImageProviderInfo]


@router.get("/info", response_model=ToolkitInfo)
async def info() -> ToolkitInfo:
    return ToolkitInfo(
        formats={f.value: FORMAT_DIMS[f] for f in ImageFormat},
        rembg_available=rembg_available(),
        providers=[p.info() for p in all_image_providers()],
    )


# ---------------------------------------------------------------- Assets --- #
@router.get("/assets", response_model=list[DesignAsset])
async def assets() -> list[DesignAsset]:
    return list_assets()


@router.get("/assets/{asset_id}", response_model=DesignAsset)
async def asset_detail(asset_id: str) -> DesignAsset:
    a = get_asset(asset_id)
    if a is None:
        raise HTTPException(404, "Asset introuvable.")
    return a


@router.delete("/assets/{asset_id}")
async def asset_delete(asset_id: str) -> dict:
    if not delete_asset(asset_id):
        raise HTTPException(404, "Asset introuvable.")
    return {"status": "deleted"}


@router.post("/upload", response_model=DesignAsset)
async def upload(file: UploadFile = File(...),
                 name: str | None = Form(None)) -> DesignAsset:
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide.")
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image trop volumineuse (max 20 Mo).")
    try:
        return await svc.import_upload(data, name or (file.filename or "upload"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, str(exc)) from exc


class ImportUrlRequest(BaseModel):
    url: str
    name: str | None = None


@router.post("/import-url", response_model=DesignAsset)
async def import_url_ep(req: ImportUrlRequest) -> DesignAsset:
    try:
        return await svc.import_url(req.url, req.name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, str(exc)) from exc


# ---------------------------------------------------------------- Jobs --- #
class GenerateRequest(BaseModel):
    prompt: str
    format: ImageFormat = ImageFormat.SQUARE
    provider: str | None = None
    model: str | None = None
    tier: Tier = Tier.FREE
    seed: int | None = None


@router.post("/generate", response_model=DesignJob)
async def generate(req: GenerateRequest, background: BackgroundTasks) -> DesignJob:
    job = save_job(DesignJob(kind="generate"))
    background.add_task(
        svc.run_generate_job, job.id, req.prompt, req.format.value,
        req.provider, req.model, req.tier.value, req.seed,
    )
    return job


class RemoveBgRequest(BaseModel):
    asset_id: str


@router.post("/remove-bg", response_model=DesignJob)
async def remove_bg(req: RemoveBgRequest, background: BackgroundTasks) -> DesignJob:
    if get_asset(req.asset_id) is None:
        raise HTTPException(404, "Asset introuvable.")
    if not rembg_available():
        raise HTTPException(503, "rembg n'est pas installé (`pip install rembg[cpu]`).")
    job = save_job(DesignJob(kind="remove_bg"))
    background.add_task(svc.run_remove_bg_job, job.id, req.asset_id)
    return job


class ResizeRequest(BaseModel):
    asset_id: str
    formats: list[ImageFormat] = Field(min_length=1)


@router.post("/resize", response_model=DesignJob)
async def resize(req: ResizeRequest, background: BackgroundTasks) -> DesignJob:
    if get_asset(req.asset_id) is None:
        raise HTTPException(404, "Asset introuvable.")
    job = save_job(DesignJob(kind="resize"))
    background.add_task(svc.run_resize_job, job.id, req.asset_id, [f.value for f in req.formats])
    return job


class ComposeRequest(BaseModel):
    composition: Composition
    watermark: str | None = None


@router.post("/compose", response_model=DesignJob)
async def compose_ep(req: ComposeRequest, background: BackgroundTasks) -> DesignJob:
    job = save_job(DesignJob(kind="compose"))
    background.add_task(svc.run_compose_job, job.id, req.composition, req.watermark)
    return job


# ---------------------------------------------------------- Templates --- #
class QuoteCardRequest(BaseModel):
    text: str
    author: str | None = None
    format: ImageFormat = ImageFormat.SQUARE
    watermark: str | None = None
    palette: dict[str, str] | None = None


@router.post("/templates/quote-card", response_model=DesignJob)
async def template_quote_card(req: QuoteCardRequest, background: BackgroundTasks) -> DesignJob:
    comp = svc.quote_card(req.text, req.author, req.format, req.palette)
    job = save_job(DesignJob(kind="compose"))
    background.add_task(svc.run_compose_job, job.id, comp, req.watermark)
    return job


@router.get("/jobs/{job_id}", response_model=DesignJob)
async def job_detail(job_id: str) -> DesignJob:
    j = get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job introuvable.")
    return j
