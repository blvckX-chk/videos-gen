"""Routes du montage : timelines et rendu."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from ..identity.deps import current_entitlements
from ..identity.schema import Entitlements
from ..montage.schema import MontageJob, Timeline
from ..montage.service import run_montage
from ..montage.storage import (
    delete_timeline,
    get_job,
    get_timeline,
    list_jobs,
    list_timelines,
    save_job,
    save_timeline,
)

router = APIRouter(prefix="/api/montage")


# ------------------------------------------------------------ Timelines --- #
@router.get("/timelines", response_model=list[Timeline])
async def timelines(limit: int = 50) -> list[Timeline]:
    return list_timelines(limit)


@router.get("/timelines/{tid}", response_model=Timeline)
async def timeline_detail(tid: str) -> Timeline:
    t = get_timeline(tid)
    if t is None:
        raise HTTPException(404, "Timeline introuvable.")
    return t


@router.post("/timelines", response_model=Timeline)
async def timeline_save(timeline: Timeline) -> Timeline:
    """Crée ou met à jour une timeline (le client renvoie l'objet édité)."""
    timeline.touch()
    return save_timeline(timeline)


@router.delete("/timelines/{tid}")
async def timeline_delete(tid: str) -> dict:
    if not delete_timeline(tid):
        raise HTTPException(404, "Timeline introuvable.")
    return {"status": "deleted"}


# --------------------------------------------------------------- Rendu --- #
class RenderRequest(BaseModel):
    """Soit l'id d'une timeline enregistrée, soit la timeline complète."""
    timeline_id: str | None = None
    timeline: Timeline | None = None
    remove_watermark: bool = False
    watermark_text: str | None = None
    charte_id: str | None = None


@router.post("/render", response_model=MontageJob)
async def render(req: RenderRequest, background: BackgroundTasks,
                 ent: Entitlements = Depends(current_entitlements)) -> MontageJob:
    if req.timeline is None and req.timeline_id is None:
        raise HTTPException(400, "timeline ou timeline_id requis.")

    timeline = req.timeline or get_timeline(req.timeline_id)  # type: ignore[arg-type]
    if timeline is None:
        raise HTTPException(404, "Timeline introuvable.")
    if not timeline.clips:
        raise HTTPException(400, "La timeline ne contient aucun plan.")

    # Le rôle authentifié pilote le filigrane — jamais le client.
    timeline.role = ent.role.value
    timeline.remove_watermark = req.remove_watermark
    timeline.watermark_text = req.watermark_text
    if req.charte_id is not None:
        timeline.charte_id = req.charte_id
    timeline.touch()
    save_timeline(timeline)

    job = save_job(MontageJob(timeline_id=timeline.id,
                              clips_total=len(timeline.clips)))
    background.add_task(run_montage, job, timeline)
    return job


@router.get("/jobs", response_model=list[MontageJob])
async def jobs(limit: int = 30) -> list[MontageJob]:
    return list_jobs(limit)


@router.get("/jobs/{jid}", response_model=MontageJob)
async def job_detail(jid: str) -> MontageJob:
    j = get_job(jid)
    if j is None:
        raise HTTPException(404, "Job introuvable.")
    return j
