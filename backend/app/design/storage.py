"""Stockage sur disque et registre en mémoire des assets/jobs design.

Les images vivent dans `storage/design/<asset_id>.<ext>`. Servi par la route
statique `/design/*` montée dans `main.py`.
"""
from __future__ import annotations

from pathlib import Path

from ..render.service import storage_root
from .schema import DesignAsset, DesignJob

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
    return asset


def get_asset(asset_id: str) -> DesignAsset | None:
    return _ASSETS.get(asset_id)


def list_assets() -> list[DesignAsset]:
    return sorted(_ASSETS.values(), key=lambda a: a.created_at, reverse=True)


def delete_asset(asset_id: str) -> bool:
    a = _ASSETS.pop(asset_id, None)
    if a is None:
        return False
    for ext in ("png", "jpg", "webp"):
        p = asset_path(asset_id, ext)
        if p.exists():
            p.unlink()
    return True


def save_job(job: DesignJob) -> DesignJob:
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> DesignJob | None:
    return _JOBS.get(job_id)
