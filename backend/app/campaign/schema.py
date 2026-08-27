"""Schémas du super-agent unifié.

Un `Campaign` = un plan **multi-modalités** (image + vidéo + audio) produit
depuis une intention et un document optionnel. Chaque `CampaignStep` est
typé et sera exécuté par le module approprié (design / storyboard+render /
audio). C'est le vrai super-agent de la vision blvckUnlimited.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from ..design.schema import ImageFormat
from ..models import Tier


class DeliverableKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class StepType(str, Enum):
    """Trois types d'étapes couvrent tous les livrables."""
    IMAGE_TEMPLATE = "image_template"      # design/templates → PNG
    IMAGE_GENERATE = "image_generate"      # design providers → PNG
    VIDEO_STORYBOARD = "video_storyboard"  # storyboard → Remotion → MP4


class CampaignStep(BaseModel):
    """Une étape typée du plan. Les champs pertinents dépendent de `type`
    — on garde tout dans une seule classe pour simplifier l'UI et le LLM."""
    type: StepType
    kind: DeliverableKind
    label: str                              # court, lisible ("Reel 30s résumé")

    # image_template
    template: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)

    # image_generate
    prompt: Optional[str] = None
    provider: Optional[str] = None

    # commun image
    image_format: ImageFormat = ImageFormat.SQUARE

    # video_storyboard : on décrit le brief à passer au générateur existant
    duration_seconds: int = 30
    video_aspect: str = "9:16"
    tone: Optional[str] = None
    focus: Optional[str] = None             # angle éditorial

    rationale: Optional[str] = None


class Deliverable(BaseModel):
    """Un livrable produit par une étape — URL + métadonnées d'affichage."""
    kind: DeliverableKind
    label: str
    url: str
    #: aperçu image (utile pour la vidéo → poster frame)
    thumbnail_url: Optional[str] = None
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    step_index: int = 0


class Campaign(BaseModel):
    """Le plan complet — persisté à titre indicatif, éditable avant run."""
    id: str = Field(default_factory=lambda: uuid4().hex)
    intent: str
    document_id: Optional[str] = None
    tier: Tier = Tier.FREE
    generator: str = "rule_based"           # rule_based | anthropic | openai
    steps: list[CampaignStep] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CampaignJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"                     # certaines étapes ont échoué
    FAILED = "failed"


class StepError(BaseModel):
    step_index: int
    step_label: str
    message: str


class CampaignJob(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    campaign_id: str
    status: CampaignJobStatus = CampaignJobStatus.QUEUED
    steps_total: int = 0
    steps_completed: int = 0
    deliverables: list[Deliverable] = []
    errors: list[StepError] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
