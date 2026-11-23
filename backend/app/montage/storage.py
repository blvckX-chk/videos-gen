"""Persistance des timelines et des jobs de montage."""
from __future__ import annotations

import logging

from .. import db
from .schema import MontageJob, MontageJobStatus, Timeline

logger = logging.getLogger("videos_gen.montage")

_TL_COLLECTION = "timelines"
_JOB_COLLECTION = "montage_jobs"
_TIMELINES: dict[str, Timeline] = {}
_JOBS: dict[str, MontageJob] = {}


def save_timeline(t: Timeline) -> Timeline:
    _TIMELINES[t.id] = t
    db.put(_TL_COLLECTION, t.id, t.model_dump(mode="json"))
    return t


def get_timeline(tid: str) -> Timeline | None:
    return _TIMELINES.get(tid)


def list_timelines(limit: int = 50) -> list[Timeline]:
    return sorted(_TIMELINES.values(), key=lambda t: t.created_at, reverse=True)[:limit]


def delete_timeline(tid: str) -> bool:
    existed = _TIMELINES.pop(tid, None) is not None
    db.delete(_TL_COLLECTION, tid)
    return existed


def save_job(j: MontageJob) -> MontageJob:
    _JOBS[j.id] = j
    db.put(_JOB_COLLECTION, j.id, j.model_dump(mode="json"))
    return j


def get_job(jid: str) -> MontageJob | None:
    return _JOBS.get(jid)


def list_jobs(limit: int = 50) -> list[MontageJob]:
    return sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)[:limit]


def rehydrate() -> int:
    """Recharge timelines et jobs ; un job interrompu par un redémarrage est
    marqué échoué (pas de spinner infini côté UI)."""
    _TIMELINES.clear()
    _JOBS.clear()
    for data in db.all(_TL_COLLECTION):
        try:
            t = Timeline.model_validate(data)
            _TIMELINES[t.id] = t
        except Exception:  # noqa: BLE001
            logger.warning("Timeline illisible ignorée", exc_info=True)
    for data in db.all(_JOB_COLLECTION):
        try:
            j = MontageJob.model_validate(data)
        except Exception:  # noqa: BLE001
            logger.warning("Job de montage illisible ignoré", exc_info=True)
            continue
        if j.status in (MontageJobStatus.QUEUED, MontageJobStatus.RUNNING):
            j.status = MontageJobStatus.FAILED
            j.error = "Interrompu par un redémarrage du serveur."
            j.touch()
            db.put(_JOB_COLLECTION, j.id, j.model_dump(mode="json"))
        _JOBS[j.id] = j
    return len(_TIMELINES) + len(_JOBS)
