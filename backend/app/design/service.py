"""Service haut niveau du module Graphic Design.

Coordonne : providers d'images, opérations de traitement (PIL) et composer.
Respecte le contrat blueprint v1.1 : un job `free` ne peut appeler qu'un
provider `free=True`.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import httpx
from PIL import Image

from ..models import Tier
from . import processing
from .composer import apply_watermark, compose
from .providers.base import ImageProvider
from .providers.registry import default_image_provider, get_image_provider
from .schema import (
    AssetKind,
    Composition,
    DesignAsset,
    DesignJob,
    DesignJobStatus,
    FORMAT_DIMS,
    ImageFormat,
)
from .storage import asset_path, get_asset, get_job, save_asset, save_job

logger = logging.getLogger("videos_gen.design")


def _dims_for_format(fmt: ImageFormat | str) -> tuple[int, int]:
    return FORMAT_DIMS[ImageFormat(fmt) if isinstance(fmt, str) else fmt]


def _asset_from_image(img: Image.Image, name: str, kind: AssetKind,
                       provider: str | None = None, prompt: str | None = None,
                       parent_id: str | None = None,
                       format: str | None = None) -> DesignAsset:
    asset = DesignAsset(name=name, kind=kind, url="", provider=provider,
                        prompt=prompt, parent_id=parent_id, format=format)
    # PNG toujours (préserve l'alpha des overlays / rembg)
    out = asset_path(asset.id, "png")
    w, h, size = processing.save_image(img, out)
    asset.width = w; asset.height = h; asset.size_bytes = size
    asset.url = f"/design/{out.name}"
    return save_asset(asset)


def _pick_provider(provider_id: str | None, tier: Tier) -> ImageProvider:
    prov = get_image_provider(provider_id) if provider_id else default_image_provider()
    if prov is None:
        raise RuntimeError(f"Provider inconnu : {provider_id}")
    if not prov.is_available():
        req = prov.requires_key or ""
        raise RuntimeError(f"Provider '{prov.id}' indisponible" + (f" (clé {req} manquante)" if req else "."))
    # Garde-fou tier free : refuse un provider payant (contrat v1.1)
    if tier == Tier.FREE and not prov.free:
        raise PermissionError(f"Le provider '{prov.id}' est payant et interdit sur un job free.")
    return prov


# --------------------------------------------------------------------------- #
# Runners de job — appelés en arrière-plan.
# --------------------------------------------------------------------------- #
async def run_generate_job(
    job_id: str, prompt: str, format: str, provider_id: str | None,
    model: str | None, tier: str, seed: int | None,
) -> None:
    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = DesignJobStatus.RUNNING
        job.touch()
        w, h = _dims_for_format(format)
        prov = _pick_provider(provider_id, Tier(tier))
        img = await prov.generate(prompt=prompt, width=w, height=h, model=model, seed=seed)
        # normalise à la taille cible (Pollinations peut arrondir aux multiples de 64)
        img = processing.fit_cover(img.convert("RGBA"), w, h)
        asset = _asset_from_image(
            img, name=prompt[:60] or "sans titre",
            kind=AssetKind.GENERATED, provider=prov.id, prompt=prompt, format=format,
        )
        job.output_asset_ids = [asset.id]
        job.status = DesignJobStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.exception("génération design %s échouée", job_id)
        job.status = DesignJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)


async def run_remove_bg_job(job_id: str, asset_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = DesignJobStatus.RUNNING
        job.touch()
        parent = get_asset(asset_id)
        if parent is None:
            raise RuntimeError("Asset introuvable.")
        src = _load_asset_image(parent)
        out = processing.remove_background(src)
        asset = _asset_from_image(
            out, name=f"{parent.name} — sans fond",
            kind=AssetKind.PROCESSED, parent_id=parent.id, format=parent.format,
        )
        job.output_asset_ids = [asset.id]
        job.status = DesignJobStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.exception("remove_bg %s échoué", job_id)
        job.status = DesignJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)


async def run_resize_job(job_id: str, asset_id: str, formats: list[str]) -> None:
    """Décline un asset en plusieurs formats via recadrage intelligent."""
    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = DesignJobStatus.RUNNING
        job.touch()
        parent = get_asset(asset_id)
        if parent is None:
            raise RuntimeError("Asset introuvable.")
        src = _load_asset_image(parent)
        out_ids: list[str] = []
        for f in formats:
            w, h = _dims_for_format(f)
            img = processing.fit_cover(src, w, h)
            a = _asset_from_image(
                img, name=f"{parent.name} — {f}",
                kind=AssetKind.PROCESSED, parent_id=parent.id, format=f,
            )
            out_ids.append(a.id)
        job.output_asset_ids = out_ids
        job.status = DesignJobStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.exception("resize %s échoué", job_id)
        job.status = DesignJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)


async def run_plan_job(job_id: str, plan_steps: list, tier_value: str,
                        watermark: str | None = None) -> None:
    """Exécute un plan complet de l'agent : chaque étape produit un asset.

    On accepte `plan_steps` en `list` brut (dict) plutôt que typée pour ne pas
    créer d'import circulaire ; la validation typée est faite à l'entrée par
    le router."""
    from .agent import PlanStep  # imports différés
    from .templates import build_template

    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = DesignJobStatus.RUNNING
        job.touch()

        out_ids: list[str] = []
        for raw in plan_steps:
            step = raw if isinstance(raw, PlanStep) else PlanStep(**raw)
            if step.type == "template":
                if not step.template:
                    continue
                comp = build_template(step.template, dict(step.params))
                img = compose(comp)
                if watermark:
                    img = apply_watermark(img, watermark)
                asset = _asset_from_image(
                    img, name=comp.name, kind=AssetKind.COMPOSED,
                    format=str(comp.format),
                )
                out_ids.append(asset.id)
            elif step.type == "generate":
                if not step.prompt:
                    continue
                w, h = _dims_for_format(step.format)
                prov = _pick_provider(step.provider, Tier(tier_value))
                img = await prov.generate(prompt=step.prompt, width=w, height=h)
                img = processing.fit_cover(img.convert("RGBA"), w, h)
                asset = _asset_from_image(
                    img, name=(step.prompt or "")[:60] or "génération",
                    kind=AssetKind.GENERATED, provider=prov.id,
                    prompt=step.prompt, format=step.format.value,
                )
                out_ids.append(asset.id)
        job.output_asset_ids = out_ids
        job.status = DesignJobStatus.SUCCEEDED if out_ids else DesignJobStatus.FAILED
        if not out_ids:
            job.error = "Le plan n'a produit aucun asset."
    except Exception as exc:  # noqa: BLE001
        logger.exception("exécution plan %s échouée", job_id)
        job.status = DesignJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)


async def run_compose_job(job_id: str, comp: Composition,
                           watermark: str | None = None) -> None:
    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = DesignJobStatus.RUNNING
        job.touch()
        img = compose(comp)
        if watermark:
            img = apply_watermark(img, watermark)
        asset = _asset_from_image(
            img, name=comp.name,
            kind=AssetKind.COMPOSED, format=str(comp.format),
        )
        job.output_asset_ids = [asset.id]
        job.status = DesignJobStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.exception("compose %s échoué", job_id)
        job.status = DesignJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)


# --------------------------------------------------------------------------- #
# Templates prêts à l'emploi — voir `design/templates.py`.
# On ré-exporte `quote_card` pour la rétrocompatibilité du router.
# --------------------------------------------------------------------------- #
from .templates import quote_card  # noqa: E402,F401


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_asset_image(asset: DesignAsset) -> Image.Image:
    for ext in ("png", "jpg", "webp"):
        p = asset_path(asset.id, ext)
        if p.exists():
            return Image.open(p).convert("RGBA")
    raise FileNotFoundError(f"Fichier introuvable pour l'asset {asset.id}")


async def import_upload(data: bytes, name: str) -> DesignAsset:
    """Import direct d'une image uploadée par l'utilisateur."""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Image invalide : {exc}") from exc
    return _asset_from_image(img, name=name, kind=AssetKind.UPLOADED)


async def import_url(url: str, name: str | None = None) -> DesignAsset:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        r = await c.get(url); r.raise_for_status()
    return await import_upload(r.content, name or Path(url).name or "image")
