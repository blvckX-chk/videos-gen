"""Schémas de la console conversationnelle KORA."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    tier: str = "free"


class ChatResult(BaseModel):
    #: text | campaign_plan | copy | image_job | image | help
    type: str = "text"
    text: Optional[str] = None
    #: charge utile structurée (plan, copy, job, asset…) rendue par l'UI
    data: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str                 # phrase de KORA
    intent: str                # intention détectée
    engine: str = "rule_based" # rule_based | anthropic | openai
    result: ChatResult = ChatResult()
