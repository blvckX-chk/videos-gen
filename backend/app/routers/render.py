"""Routes du Slice 3 : rendu du storyboard en MP4."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from ..models import Job, Tier
from ..render.service import create_render_job, is_render_available, run_render
from ..services.jobs import get_job
from ..storyboard.schema import Storyboard

router = APIRouter(prefix="/api")


class RenderRequest(BaseModel):
    storyboard: Storyboard
    tier: Tier = Tier.FREE
    client_id: str | None = None
    # Slice 4 — post-production
    narration: bool = False
    captions: bool = False
    voice_provider: str | None = None
    music_clip_id: str | None = None


@router.post("/render", response_model=Job)
async def render(req: RenderRequest, background: BackgroundTasks, request: Request) -> Job:
    if not is_render_available():
        raise HTTPException(
            503,
            "Le rendu Remotion n'est pas disponible sur ce serveur "
            "(Node/Chromium manquant ou projet remotion/ absent).",
        )
    job = create_render_job(req.storyboard, tier=req.tier.value, client_id=req.client_id)

    # URL absolue vers les assets — Remotion (chromium) doit pouvoir la fetcher.
    assets_base = str(request.base_url).rstrip("/") + "/assets"
    background.add_task(
        run_render, job.id, req.storyboard, assets_base, None,
        req.narration, req.captions, req.voice_provider, req.music_clip_id,
    )
    return job


@router.get("/voices")
async def voices() -> list[dict]:
    """Providers TTS disponibles (pour l'UI du rendu)."""
    from ..voice.providers.registry import all_tts_providers
    return [p.info().model_dump() for p in all_tts_providers()]


@router.get("/render/{job_id}", response_model=Job)
async def render_status(job_id: str) -> Job:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Rendu introuvable")
    return job
