"""Routes du super-agent unifié — planifier et exécuter une campagne SMM
multi-modalités depuis une intention et un document optionnel."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from ..campaign.executor import execute_campaign
from ..campaign.planner import plan_campaign
from ..campaign.schema import Campaign, CampaignJob
from ..campaign.storage import get_campaign, get_job, list_jobs, save_campaign, save_job
from ..models import Tier

router = APIRouter(prefix="/api/campaign")


class PlanRequest(BaseModel):
    intent: str
    document_id: str | None = None
    tier: Tier = Tier.FREE


@router.post("/plan", response_model=Campaign)
async def plan(req: PlanRequest) -> Campaign:
    """Dry-run : propose un plan de campagne, sans l'exécuter (validation
    humaine, blueprint v1.1). Sauvegardé pour ré-exécution ultérieure."""
    c = await plan_campaign(req.intent, req.document_id, req.tier)
    return save_campaign(c)


class RunRequest(BaseModel):
    """Deux façons d'exécuter : soit référencer un plan existant (par id),
    soit passer un plan complet (éventuellement édité côté UI)."""
    campaign_id: str | None = None
    campaign: Campaign | None = None
    watermark: str | None = "blvckUnlimited"


@router.post("/run", response_model=CampaignJob)
async def run(req: RunRequest, background: BackgroundTasks, request: Request) -> CampaignJob:
    if req.campaign is None and req.campaign_id is None:
        raise HTTPException(400, "campaign ou campaign_id requis.")

    if req.campaign is not None:
        campaign = save_campaign(req.campaign)
    else:
        campaign = get_campaign(req.campaign_id)  # type: ignore[arg-type]
        if campaign is None:
            raise HTTPException(404, "Campagne introuvable.")

    job = save_job(CampaignJob(campaign_id=campaign.id, steps_total=len(campaign.steps)))
    assets_base = str(request.base_url).rstrip("/") + "/assets"
    background.add_task(execute_campaign, job, campaign, assets_base, req.watermark)
    return job


@router.get("/jobs", response_model=list[CampaignJob])
async def jobs(limit: int = 20) -> list[CampaignJob]:
    return list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=CampaignJob)
async def job_detail(job_id: str) -> CampaignJob:
    j = get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job introuvable.")
    return j
