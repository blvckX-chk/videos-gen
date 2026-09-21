"""Routes du super-agent unifié — planifier et exécuter une campagne SMM
multi-modalités depuis une intention et un document optionnel."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from ..campaign.executor import execute_campaign
from ..campaign.planner import plan_campaign
from ..campaign.schema import Campaign, CampaignJob
from ..campaign.storage import get_campaign, get_job, list_jobs, save_campaign, save_job
from ..identity.deps import current_entitlements
from ..identity.entitlements import effective_tier
from ..identity.schema import Entitlements
from ..models import Tier

router = APIRouter(prefix="/api/campaign")


class PlanRequest(BaseModel):
    intent: str
    document_id: str | None = None
    tier: Tier = Tier.FREE
    charte_id: str | None = None


@router.post("/plan", response_model=Campaign)
async def plan(req: PlanRequest,
               ent: Entitlements = Depends(current_entitlements)) -> Campaign:
    """Dry-run : propose un plan de campagne, sans l'exécuter (validation
    humaine, blueprint v1.1). Sauvegardé pour ré-exécution ultérieure."""
    c = await plan_campaign(req.intent, req.document_id,
                            Tier(effective_tier(ent, req.tier.value)))
    c.role = ent.role.value
    c.charte_id = req.charte_id
    return save_campaign(c)


class RunRequest(BaseModel):
    """Deux façons d'exécuter : soit référencer un plan existant (par id),
    soit passer un plan complet (éventuellement édité côté UI)."""
    campaign_id: str | None = None
    campaign: Campaign | None = None
    charte_id: str | None = None
    remove_watermark: bool = False
    watermark_text: str | None = None


@router.post("/run", response_model=CampaignJob)
async def run(req: RunRequest, background: BackgroundTasks, request: Request,
              ent: Entitlements = Depends(current_entitlements)) -> CampaignJob:
    if req.campaign is None and req.campaign_id is None:
        raise HTTPException(400, "campaign ou campaign_id requis.")

    if req.campaign is not None:
        campaign = req.campaign
    else:
        campaign = get_campaign(req.campaign_id)  # type: ignore[arg-type]
        if campaign is None:
            raise HTTPException(404, "Campagne introuvable.")

    # Rôle + marque (le rôle contraint le tier et le droit de retirer le filigrane)
    campaign.role = ent.role.value
    campaign.tier = Tier(effective_tier(ent, campaign.tier.value))
    if req.charte_id is not None:
        campaign.charte_id = req.charte_id
    campaign.remove_watermark = req.remove_watermark
    campaign.watermark_text = req.watermark_text
    save_campaign(campaign)

    job = save_job(CampaignJob(campaign_id=campaign.id, steps_total=len(campaign.steps)))
    assets_base = str(request.base_url).rstrip("/") + "/assets"
    background.add_task(execute_campaign, job, campaign, assets_base)
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
