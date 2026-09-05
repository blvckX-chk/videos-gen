"""Exécuteur du plan de campagne.

Dispatche chaque `CampaignStep` vers le module compétent :
  - `image_template`   → design.templates.build_template + composer
  - `image_generate`   → design providers (Pollinations / fal / …)
  - `video_storyboard` → storyboard.generator + render.service (Remotion)

Ne lève jamais globalement : les échecs par étape sont capturés dans
`CampaignJob.errors`, et le job passe à `PARTIAL` si au moins une étape
a réussi (patron « best-effort » utile pour ne pas perdre un batch
entier à cause d'un provider indisponible).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ..design import processing
from ..design.composer import apply_watermark, compose
from ..design.providers.registry import get_image_provider
from ..design.schema import AssetKind, ImageFormat, FORMAT_DIMS
from ..design.service import _asset_from_image
from ..design.templates import build_template
from ..ingestion.schema import DocType
from ..models import Tier
from ..render.service import create_render_job, run_render, storage_root
from ..services.clarification import Brief
from ..services.documents import get_document
from ..storyboard.generator import generate_storyboard
from ..storyboard.schema import Storyboard
from .schema import (
    Campaign,
    CampaignJob,
    CampaignJobStatus,
    CampaignStep,
    Deliverable,
    DeliverableKind,
    StepError,
    StepType,
)

logger = logging.getLogger("videos_gen.campaign")


def _brief_from_step(step: CampaignStep, document_id: str) -> Brief:
    """Construit un Brief minimal pour piloter le générateur de storyboard."""
    doc = get_document(document_id)
    return Brief(
        document_id=document_id,
        doc_type=doc.doc_type if doc else DocType.MIXED,
        objective=step.focus or "Informer / résumer",
        audience="Grand public",
        tone=step.tone or "dynamique",
        language="fr",
        duration_seconds=step.duration_seconds,
        answers={"source": "campaign_agent"},
    )


async def _run_image_template(step: CampaignStep,
                              watermark: str | None) -> Deliverable:
    if not step.template:
        raise RuntimeError("template manquant sur une étape image_template.")
    params = dict(step.params)
    # Injecte le format si absent
    params.setdefault("format", step.image_format.value)
    comp = build_template(step.template, params)
    img = compose(comp)
    if watermark:
        img = apply_watermark(img, watermark)
    asset = _asset_from_image(
        img, name=step.label, kind=AssetKind.COMPOSED,
        format=str(comp.format),
    )
    return Deliverable(
        kind=DeliverableKind.IMAGE, label=step.label, url=asset.url,
        thumbnail_url=asset.url, width=asset.width, height=asset.height,
    )


async def _run_image_generate(step: CampaignStep, tier: Tier) -> Deliverable:
    if not step.prompt:
        raise RuntimeError("prompt manquant sur une étape image_generate.")
    prov = get_image_provider(step.provider or "pollinations")
    if prov is None or not prov.is_available():
        raise RuntimeError(f"Provider indisponible : {step.provider}")
    if tier == Tier.FREE and not prov.free:
        raise PermissionError(f"Provider '{prov.id}' interdit sur tier free.")
    w, h = FORMAT_DIMS[step.image_format]
    img = await prov.generate(prompt=step.prompt, width=w, height=h)
    img = processing.fit_cover(img.convert("RGBA"), w, h)
    asset = _asset_from_image(
        img, name=step.label, kind=AssetKind.GENERATED,
        provider=prov.id, prompt=step.prompt, format=step.image_format.value,
    )
    return Deliverable(
        kind=DeliverableKind.IMAGE, label=step.label, url=asset.url,
        thumbnail_url=asset.url, width=asset.width, height=asset.height,
    )


async def _run_video_storyboard(step: CampaignStep, campaign: Campaign,
                                assets_base_url: str) -> Deliverable:
    if not campaign.document_id:
        raise RuntimeError("Vidéo depuis storyboard : document_id requis.")
    doc = get_document(campaign.document_id)
    if doc is None:
        raise RuntimeError("Document introuvable pour cette campagne.")

    brief = _brief_from_step(step, campaign.document_id)
    sb: Storyboard = await generate_storyboard(doc, brief)
    # Forcer le ratio demandé par la campagne
    sb.formats = [step.video_aspect] + [f for f in sb.formats if f != step.video_aspect]

    render_job = create_render_job(sb, tier=campaign.tier.value)
    # On attend la fin (l'executor est déjà dans une tâche de fond, donc bloquer ici est OK).
    # Slice 4 : voix off + sous-titres activés par défaut pour les Reels de campagne.
    await run_render(render_job.id, sb, assets_base_url, None,
                     narration=True, captions=True)
    from ..services.jobs import get_job as get_render_job
    rj = get_render_job(render_job.id)
    if rj is None or rj.status.value != "succeeded" or not rj.video_url:
        raise RuntimeError(f"Rendu vidéo échoué : {rj.error if rj else 'inconnu'}")

    return Deliverable(
        kind=DeliverableKind.VIDEO, label=step.label, url=rj.video_url,
        duration_seconds=float(sb.total_duration),
    )


async def execute_campaign(job: CampaignJob, campaign: Campaign,
                            assets_base_url: str,
                            watermark: str | None = "blvckUnlimited") -> None:
    """Exécute toutes les étapes de la campagne, tolérant aux échecs partiels."""
    job.status = CampaignJobStatus.RUNNING
    job.steps_total = len(campaign.steps)
    job.touch()
    from .storage import save_job
    save_job(job)

    for i, step in enumerate(campaign.steps):
        try:
            if step.type == StepType.IMAGE_TEMPLATE:
                deliv = await _run_image_template(step, watermark)
            elif step.type == StepType.IMAGE_GENERATE:
                deliv = await _run_image_generate(step, campaign.tier)
            elif step.type == StepType.VIDEO_STORYBOARD:
                deliv = await _run_video_storyboard(step, campaign, assets_base_url)
            else:
                raise RuntimeError(f"Type d'étape inconnu : {step.type}")
            deliv.step_index = i
            job.deliverables.append(deliv)
            job.steps_completed += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("étape %d (%s) échouée", i, step.label)
            job.errors.append(StepError(
                step_index=i, step_label=step.label, message=str(exc),
            ))
        finally:
            job.touch()
            save_job(job)

    # Statut final
    if not job.deliverables:
        job.status = CampaignJobStatus.FAILED
    elif job.errors:
        job.status = CampaignJobStatus.PARTIAL
    else:
        job.status = CampaignJobStatus.SUCCEEDED
    job.touch()
    save_job(job)
