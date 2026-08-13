"""Schémas Pydantic partagés par l'API."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    ENHANCING = "enhancing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Description de la vidéo à générer")
    provider: str = Field("demo", description="Identifiant du provider (voir /api/providers)")
    model: Optional[str] = Field(None, description="Modèle spécifique du provider, sinon défaut")
    enhance: bool = Field(True, description="Améliorer automatiquement le prompt pour le réalisme")
    duration: int = Field(5, ge=1, le=30, description="Durée cible en secondes")
    aspect_ratio: str = Field("16:9", description="Ratio ex: 16:9, 9:16, 1:1")
    seed: Optional[int] = Field(None, description="Graine pour la reproductibilité")


class Job(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    status: JobStatus = JobStatus.QUEUED
    provider: str
    model: Optional[str] = None
    prompt: str
    enhanced_prompt: Optional[str] = None
    duration: int = 5
    aspect_ratio: str = "16:9"
    seed: Optional[int] = None
    video_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class ProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    free: bool
    models: list[str] = []
    requires_key: Optional[str] = None
