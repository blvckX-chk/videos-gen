"""Gestion des jobs de génération (cache mémoire + persistance SQLite).

Le dict `_JOBS` sert de cache write-through : chaque `create_job`/`save_job`
écrit aussi en base (`db`), et `rehydrate()` recharge l'état au démarrage →
un job survit à un redémarrage. Pour un vrai scale : Redis + file (Celery/arq).
"""
from __future__ import annotations

import logging

from .. import db
from ..models import Job, JobStatus
from ..providers.registry import get_provider
from .prompt_enhancer import enhance_prompt

logger = logging.getLogger("videos_gen.jobs")

_COLLECTION = "jobs"
_JOBS: dict[str, Job] = {}


def save_job(job: Job) -> Job:
    """Écrit le job en cache **et** en base (write-through)."""
    _JOBS[job.id] = job
    db.put(_COLLECTION, job.id, job.model_dump(mode="json"))
    return job


# Alias historique : la création passe par le même chemin write-through.
create_job = save_job


def get_job(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def list_jobs(limit: int = 50) -> list[Job]:
    jobs = sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)
    return jobs[:limit]


def rehydrate() -> int:
    """Recharge les jobs depuis la base dans le cache mémoire (au démarrage)."""
    _JOBS.clear()
    for data in db.all(_COLLECTION):
        try:
            job = Job.model_validate(data)
            _JOBS[job.id] = job
        except Exception:  # noqa: BLE001 — un enregistrement corrompu ne bloque pas le boot
            logger.warning("Job illisible ignoré à la réhydratation", exc_info=True)
    return len(_JOBS)


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
        save_job(job)
        return

    try:
        if enhance:
            job.status = JobStatus.ENHANCING
            job.touch()
            save_job(job)
            job.enhanced_prompt = await enhance_prompt(job.prompt)
        else:
            job.enhanced_prompt = job.prompt

        job.status = JobStatus.RUNNING
        job.touch()
        save_job(job)
        job.video_url = await provider.generate(job)

        job.status = JobStatus.SUCCEEDED
        job.touch()
        save_job(job)
    except Exception as exc:  # noqa: BLE001 — on veut capturer toute défaillance provider
        logger.exception("Échec du job %s", job_id)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.touch()
        save_job(job)
