"""Routes identité : rôle courant, droits, et gestion des chartes de marque."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..identity.charters import (
    delete_charte,
    get_charte,
    list_chartes,
    propose_chartes,
    save_charte,
)
from ..identity.deps import current_entitlements
from ..identity.schema import Charte, CharteProposalRequest, Entitlements

router = APIRouter(prefix="/api/identity")


@router.get("/me", response_model=Entitlements)
async def me(ent: Entitlements = Depends(current_entitlements)) -> Entitlements:
    """Rôle courant + droits (résolus depuis X-Role / X-Admin-Secret)."""
    return ent


# ------------------------------------------------------------- Chartes --- #
@router.get("/chartes", response_model=list[Charte])
async def chartes() -> list[Charte]:
    return list_chartes()


@router.get("/chartes/{cid}", response_model=Charte)
async def charte_detail(cid: str) -> Charte:
    c = get_charte(cid)
    if c is None:
        raise HTTPException(404, "Charte introuvable.")
    return c


@router.post("/chartes", response_model=Charte)
async def charte_create(charte: Charte) -> Charte:
    """Enregistre une charte fournie (couleurs, logo, police, ton)."""
    return save_charte(charte)


@router.delete("/chartes/{cid}")
async def charte_delete(cid: str) -> dict:
    if not delete_charte(cid):
        raise HTTPException(404, "Charte introuvable.")
    return {"status": "deleted"}


@router.post("/chartes/propose", response_model=list[Charte])
async def charte_propose(req: CharteProposalRequest) -> list[Charte]:
    """Propose 2-3 pistes de charte quand le client n'en a pas.
    Les pistes ne sont PAS persistées tant que l'utilisateur n'en choisit pas
    une (via POST /chartes)."""
    return propose_chartes(req, count=3)
