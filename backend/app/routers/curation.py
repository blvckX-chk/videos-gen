"""Routes de tri et de curation des photos + état de la connexion Tchavi."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..curation import service as svc
from ..curation.schema import PhotoAnalysis, Scenario
from ..tchavi import client as tchavi

router = APIRouter(prefix="/api/curation")


class AnalyzeRequest(BaseModel):
    media_ids: list[str] | None = None


@router.post("/analyze", response_model=list[PhotoAnalysis])
async def analyze(req: AnalyzeRequest) -> list[PhotoAnalysis]:
    """Couche déterministe : note chaque photo, signale flou / exposition /
    doublons. Gratuit, aucune clé requise."""
    return svc.analyze(req.media_ids)


class ScenarioRequest(BaseModel):
    media_ids: list[str] | None = None
    #: nombre de plans souhaités (par défaut ~60 % des photos exploitables)
    target_count: int | None = None
    #: contexte éditorial, ex. « récap de bootcamp »
    theme: str | None = None
    per_photo: float = 2.5


@router.post("/scenario", response_model=Scenario)
async def scenario(req: ScenarioRequest) -> Scenario:
    """Chaîne complète : tri puis curation (vision Tchavi si configurée),
    et renvoie un montage proposé — à éditer avant rendu."""
    return await svc.build_scenario(
        req.media_ids, target_count=req.target_count,
        theme=req.theme, per_photo=req.per_photo)


@router.get("/tchavi")
async def tchavi_status() -> dict:
    """Test de connexion à Tchavi (utile pour valider la clé sur le serveur)."""
    if not tchavi.is_configured():
        return {"configured": False,
                "hint": "Ajoute TCHAVI_API_KEY dans backend/.env."}
    try:
        models = await tchavi.list_models()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Tchavi injoignable : {exc}") from exc
    ids = [m.get("id") for m in models if isinstance(m, dict) and m.get("id")]
    return {"configured": True, "models": len(ids), "sample": ids[:12]}
