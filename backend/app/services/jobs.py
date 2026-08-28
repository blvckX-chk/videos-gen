"""Gestion des jobs de génération (en mémoire) + exécution asynchrone.

Pour un MVP mono-processus, un store en mémoire suffit. Pour la production,
remplacer `_JOBS` par Redis et l'exécution par une file (Celery, RQ, arq).
"""
from __future__ import annotations

import asyncio
import logging

from ..models import Job, JobStatus
from ..providers.registry import get_provider
from .prompt_enhancer import enhance_prompt

logger = logging.getLogger("videos_gen.jobs")

_JOBS: dict[str, Job] = {}


def create_job(job: Job) -> Job:
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def list_jobs(limit: int = 50) -> list[Job]:
    jobs = sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)
    return jobs[:limit]


async def run_job(job_id: str, enhance: bool) -> None:
    """Exécute un job en tâche de fond : amélioration puis génération."""
    job = _JOBS.get(job_id)
    if job is None:
        return

    provider = get_provider(job.provider)
    if provider is None or not provider.is_available():
        job.status = JobStatus.FAILED
        job.error = f"Provider '{job.provider}' indisponible (clé manquante ?)."
        job.touch()
        return

    try:
        if enhance:
            job.status = JobStatus.ENHANCING
            job.touch()
            job.enhanced_prompt = await enhance_prompt(job.prompt)
        else:
            job.enhanced_prompt = job.prompt

        job.status = JobStatus.RUNNING
        job.touch()
        job.video_url = await provider.generate(job)

        job.status = JobStatus.SUCCEEDED
        job.touch()
    except Exception as exc:  # noqa: BLE001 — on veut capturer toute défaillance provider
        logger.exception("Échec du job %s", job_id)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.touch()
