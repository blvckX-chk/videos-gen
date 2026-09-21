"""Stockage sur disque et registre en mémoire des assets/jobs design.

Les images vivent dans `storage/design/<asset_id>.<ext>`. Servi par la route
statique `/design/*` montée dans `main.py`.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .. import db
from ..render.service import storage_root
from .schema import DesignAsset, DesignJob

logger = logging.getLogger("videos_gen.design")

_ASSETS_COLLECTION = "design_assets"
_JOBS_COLLECTION = "design_jobs"
_ASSETS: dict[str, DesignAsset] = {}
_JOBS: dict[str, DesignJob] = {}


def design_dir() -> Path:
    d = storage_root() / "design"
    d.mkdir(parents=True, exist_ok=True)
    return d


def asset_path(asset_id: str, ext: str = "png") -> Path:
    return design_dir() / f"{asset_id}.{ext}"


def save_asset(asset: DesignAsset) -> DesignAsset:
    _ASSETS[asset.id] = asset
    db.put(_ASSETS_COLLECTION, asset.id, asset.model_dump(mode="json"))
    return asset


def get_asset(asset_id: str) -> DesignAsset | None:
    return _ASSETS.get(asset_id)


def list_assets() -> list[DesignAsset]:
    return sorted(_ASSETS.values(), key=lambda a: a.created_at, reverse=True)


def delete_asset(asset_id: str) -> bool:
    a = _ASSETS.pop(asset_id, None)
    if a is None:
        return False
    db.delete(_ASSETS_COLLECTION, asset_id)
    for ext in ("png", "jpg", "webp"):
        p = asset_path(asset_id, ext)
        if p.exists():
            p.unlink()
    return True


def save_job(job: DesignJob) -> DesignJob:
    _JOBS[job.id] = job
    db.put(_JOBS_COLLECTION, job.id, job.model_dump(mode="json"))
    return job


def get_job(job_id: str) -> DesignJob | None:
    return _JOBS.get(job_id)


def rehydrate() -> int:
    """Recharge assets + jobs design depuis la base (au démarrage)."""
    _ASSETS.clear()
    _JOBS.clear()
    for data in db.all(_ASSETS_COLLECTION):
        try:
            a = DesignAsset.model_validate(data)
            _ASSETS[a.id] = a
        except Exception:  # noqa: BLE001
            logger.warning("Asset design illisible ignoré", exc_info=True)
    for data in db.all(_JOBS_COLLECTION):
        try:
            j = DesignJob.model_validate(data)
            _JOBS[j.id] = j
        except Exception:  # noqa: BLE001
            logger.warning("Job design illisible ignoré", exc_info=True)
    return len(_ASSETS) + len(_JOBS)
