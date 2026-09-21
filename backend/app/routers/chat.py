"""Route de la console conversationnelle KORA."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..chat.schema import ChatRequest, ChatResponse
from ..chat.service import handle_message
from ..identity.deps import current_entitlements
from ..identity.entitlements import effective_tier
from ..identity.schema import Entitlements

router = APIRouter(prefix="/api/chat")


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest,
               ent: Entitlements = Depends(current_entitlements)) -> ChatResponse:
    req.tier = effective_tier(ent, req.tier)
    return await handle_message(req)
