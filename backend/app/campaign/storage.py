"""Registre des campagnes et jobs de campagne : cache mémoire + persistance."""
from __future__ import annotations

import logging

from .. import db
from .schema import Campaign, CampaignJob, CampaignJobStatus, StepError

logger = logging.getLogger("videos_gen.campaign")

_CAMPAIGNS_COLLECTION = "campaigns"
_JOBS_COLLECTION = "campaign_jobs"
_CAMPAIGNS: dict[str, Campaign] = {}
_JOBS: dict[str, CampaignJob] = {}


def save_campaign(c: Campaign) -> Campaign:
    _CAMPAIGNS[c.id] = c
    db.put(_CAMPAIGNS_COLLECTION, c.id, c.model_dump(mode="json"))
    return c


def get_campaign(cid: str) -> Campaign | None:
    return _CAMPAIGNS.get(cid)


def save_job(j: CampaignJob) -> CampaignJob:
    _JOBS[j.id] = j
    db.put(_JOBS_COLLECTION, j.id, j.model_dump(mode="json"))
    return j


def get_job(jid: str) -> CampaignJob | None:
    return _JOBS.get(jid)


def list_jobs(limit: int = 50) -> list[CampaignJob]:
    return sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)[:limit]


def rehydrate() -> int:
    """Recharge campagnes + jobs depuis la base (au démarrage)."""
    _CAMPAIGNS.clear()
    _JOBS.clear()
    for data in db.all(_CAMPAIGNS_COLLECTION):
        try:
            c = Campaign.model_validate(data)
            _CAMPAIGNS[c.id] = c
        except Exception:  # noqa: BLE001
            logger.warning("Campagne illisible ignorée", exc_info=True)
    for data in db.all(_JOBS_COLLECTION):
        try:
            j = CampaignJob.model_validate(data)
        except Exception:  # noqa: BLE001
            logger.warning("Job campagne illisible ignoré", exc_info=True)
            continue
        # Orphelin (ni succeeded/partial/failed) → marqué FAILED au boot.
        if j.status in (CampaignJobStatus.QUEUED, CampaignJobStatus.RUNNING):
            j.status = CampaignJobStatus.FAILED
            j.errors.append(StepError(step_index=-1, step_label="(système)",
                                      message="Interrompu par un redémarrage du serveur."))
            j.touch()
            db.put(_JOBS_COLLECTION, j.id, j.model_dump(mode="json"))
        _JOBS[j.id] = j
    return len(_CAMPAIGNS) + len(_JOBS)
