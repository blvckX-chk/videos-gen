"""Registre en mémoire des campagnes et jobs de campagne."""
from __future__ import annotations

from .schema import Campaign, CampaignJob

_CAMPAIGNS: dict[str, Campaign] = {}
_JOBS: dict[str, CampaignJob] = {}


def save_campaign(c: Campaign) -> Campaign:
    _CAMPAIGNS[c.id] = c
    return c


def get_campaign(cid: str) -> Campaign | None:
    return _CAMPAIGNS.get(cid)


def save_job(j: CampaignJob) -> CampaignJob:
    _JOBS[j.id] = j
    return j


def get_job(jid: str) -> CampaignJob | None:
    return _JOBS.get(jid)


def list_jobs(limit: int = 50) -> list[CampaignJob]:
    return sorted(_JOBS.values(), key=lambda j: j.created_at, reverse=True)[:limit]
