"""Routes du module Copywriting."""
from __future__ import annotations

from fastapi import APIRouter

from ..copy.schema import CopyRequest, CopyResult, Platform
from ..copy.service import PLATFORM_SPECS, generate_copy

router = APIRouter(prefix="/api/copy")


@router.get("/platforms")
async def platforms() -> list[dict]:
    return [{"id": p.value, "label": PLATFORM_SPECS[p]["label"],
             "tone": PLATFORM_SPECS[p]["tone"]} for p in Platform]


@router.post("", response_model=CopyResult)
async def make_copy(req: CopyRequest) -> CopyResult:
    return await generate_copy(req)
