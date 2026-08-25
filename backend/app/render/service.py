"""Service de rendu : Storyboard → MP4 via Remotion CLI.

Chaque rendu est un `Job` (le même modèle que les générations providers).
Le champ `tier` est propagé pour permettre au Slice 4+ d'ajouter des étapes
premium (voix ElevenLabs, etc.). Le compteur de coût est incrémenté à chaque
étape externe — sur le tier FREE il reste à zéro.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from pathlib import Path
from uuid import uuid4

from ..models import CostEntry, Job, JobStatus
from ..services.documents import get_document
from ..services.jobs import _JOBS
from ..storyboard.schema import Storyboard
from .assets import prepare_assets, storage_root

logger = logging.getLogger("videos_gen.render")

REMOTION_DIR = Path(__file__).resolve().parents[3] / "remotion"
# Chromium fourni par l'environnement — remplace le download Remotion. Peut
# être surchargé via l'env var REMOTION_CHROMIUM. Compatible playwright.
DEFAULT_CHROMIUM = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"


def _output_dir() -> Path:
    d = storage_root() / "renders"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_render_job(sb: Storyboard, tier: str = "free", client_id: str | None = None) -> Job:
    from ..models import Tier
    job = Job(
        provider="remotion",
        model=sb.template,
        prompt=f"render:{sb.id}",
        duration=int(sb.total_duration) or 5,
        aspect_ratio=(sb.formats[0] if sb.formats else "9:16"),
        tier=Tier(tier),
        client_id=client_id,
    )
    _JOBS[job.id] = job
    return job


async def run_render(job_id: str, sb: Storyboard, assets_base_url: str,
                     chromium_path: str | None = None) -> None:
    job = _JOBS.get(job_id)
    if job is None:
        return
    doc = get_document(sb.document_id)
    if doc is None:
        job.status = JobStatus.FAILED
        job.error = "Document introuvable pour ce storyboard."
        job.touch()
        return

    try:
        job.status = JobStatus.RUNNING
        job.touch()

        # 1) Préparer les assets (pages/cases → JPEG dans storage/assets/…)
        sb_ready = prepare_assets(doc, sb, assets_base_url)

        # 2) Écrire les props d'entrée pour Remotion
        props_path = _output_dir() / f"{job.id}.props.json"
        out_path = _output_dir() / f"{job.id}.mp4"
        props_path.write_text(json.dumps({"storyboard": sb_ready.model_dump()}), encoding="utf-8")

        # 3) Lancer le rendu (Node fait le vrai travail)
        chromium = chromium_path or DEFAULT_CHROMIUM
        cmd = [
            "npx", "remotion", "render", "Video",
            str(out_path),
            f"--props={props_path}",
            f"--browser-executable={chromium}",
            "--log=warn",
        ]
        started = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(REMOTION_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        elapsed = time.monotonic() - started
        if proc.returncode != 0:
            tail = (out or b"").decode(errors="replace")[-800:]
            raise RuntimeError(f"Remotion a échoué (code {proc.returncode}) : {tail}")

        # 4) Compteur de coût — le rendu local est gratuit ; on trace juste le
        #    temps CPU pour le tableau de bord d'usage (facturable interne).
        job.costs.append(CostEntry(
            provider="remotion",
            kind="render_seconds",
            quantity=round(elapsed, 2),
            cost_cents=0,
            note="rendu local (cœur gratuit)",
        ))

        job.video_url = f"/renders/{out_path.name}"
        job.status = JobStatus.SUCCEEDED
        job.touch()

        # Cleanup des props (l'MP4 est conservé et servi)
        try:
            props_path.unlink()
        except OSError:
            pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("Rendu %s échoué", job_id)
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.touch()


def is_render_available() -> bool:
    """Le pipeline de rendu est-il utilisable localement ?"""
    node = shutil.which("npx") or shutil.which("node")
    return node is not None and REMOTION_DIR.exists() and Path(DEFAULT_CHROMIUM).exists()
