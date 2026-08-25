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


class Tier(str, Enum):
    """Tier de service — porté par chaque job (décision blueprint v1.1).

    - FREE : n'utilise QUE des providers gratuits (cœur open-source).
    - PREMIUM : peut activer les providers payants (ElevenLabs, HeyGen…) —
      leur coût est répercuté au client via `CostEntry`.
    Un job FREE ne doit jamais appeler un provider payant (garde-fou).
    """
    FREE = "free"
    PREMIUM = "premium"


class CostEntry(BaseModel):
    """Un poste de coût unitaire remonté par un appel externe."""
    provider: str
    kind: str                    # ex: llm_tokens, tts_seconds, render_seconds
    quantity: float = 0.0
    cost_cents: int = 0          # coût estimé en centimes USD
    note: Optional[str] = None


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
    # Décisions blueprint v1.1 (voir docs/blueprint.md, § Impact sur l'architecture)
    tier: Tier = Tier.FREE
    client_id: Optional[str] = None       # pour la facturation à l'usage
    costs: list[CostEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_cost_cents(self) -> int:
        return sum(c.cost_cents for c in self.costs)

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
