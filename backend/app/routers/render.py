"""Routes du Slice 3 : rendu du storyboard en MP4."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from ..identity.entitlements import effective_tier, resolve_entitlements
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
    # Slice 5 — marque
    charte_id: str | None = None
    remove_watermark: bool = False
    watermark_text: str | None = None


@router.post("/render", response_model=Job)
async def render(req: RenderRequest, background: BackgroundTasks, request: Request,
                 x_role: str | None = Header(default=None)) -> Job:
    if not is_render_available():
        raise HTTPException(
            503,
            "Le rendu Remotion n'est pas disponible sur ce serveur "
            "(Node/Chromium manquant ou projet remotion/ absent).",
        )
    # Le rôle contraint le tier (un free ne monte pas en premium).
    ent = resolve_entitlements(x_role)
    tier = effective_tier(ent, req.tier.value)
    job = create_render_job(req.storyboard, tier=tier, client_id=req.client_id)

    # URL absolue vers les assets — Remotion (chromium) doit pouvoir la fetcher.
    assets_base = str(request.base_url).rstrip("/") + "/assets"
    background.add_task(
        run_render, job.id, req.storyboard, assets_base, None,
        req.narration, req.captions, req.voice_provider, req.music_clip_id,
        ent.role.value, req.charte_id, req.remove_watermark, req.watermark_text,
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
