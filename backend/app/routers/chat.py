"""Route de la console conversationnelle KORA."""
from __future__ import annotations

from fastapi import APIRouter, Header

from ..chat.schema import ChatRequest, ChatResponse
from ..chat.service import handle_message
from ..identity.entitlements import effective_tier, resolve_entitlements

router = APIRouter(prefix="/api/chat")


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, x_role: str | None = Header(default=None)) -> ChatResponse:
    ent = resolve_entitlements(x_role)
    req.tier = effective_tier(ent, req.tier)
    return await handle_message(req)
