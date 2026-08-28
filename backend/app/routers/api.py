"""Routes HTTP de l'API."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..models import GenerateRequest, Job, JobStatus, ProviderInfo
from ..providers.registry import all_providers, get_provider
from ..services.jobs import create_job, get_job, list_jobs, run_job
from ..services.prompt_enhancer import enhance_prompt

router = APIRouter(prefix="/api")


@router.get("/providers", response_model=list[ProviderInfo])
async def providers() -> list[ProviderInfo]:
    return [p.info() for p in all_providers()]


@router.post("/enhance")
async def enhance(payload: dict) -> dict:
    prompt = (payload or {}).get("prompt", "").strip()
    if not prompt:
        raise HTTPException(400, "prompt requis")
    return {"enhanced_prompt": await enhance_prompt(prompt)}


@router.post("/generate", response_model=Job)
async def generate(req: GenerateRequest, background: BackgroundTasks) -> Job:
    provider = get_provider(req.provider)
    if provider is None:
        raise HTTPException(404, f"Provider inconnu: {req.provider}")
    if not provider.is_available():
        raise HTTPException(
            400,
            f"Provider '{req.provider}' indisponible. "
            f"Renseigne {provider.requires_key} dans le .env." if provider.requires_key
            else f"Provider '{req.provider}' indisponible.",
        )

    job = Job(
        provider=req.provider,
        model=req.model,
        prompt=req.prompt,
        duration=req.duration,
        aspect_ratio=req.aspect_ratio,
        seed=req.seed,
        status=JobStatus.QUEUED,
    )
    create_job(job)
    background.add_task(run_job, job.id, req.enhance)
    return job


@router.get("/jobs", response_model=list[Job])
async def jobs(limit: int = 50) -> list[Job]:
    return list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=Job)
async def job_detail(job_id: str) -> Job:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable")
    return job
