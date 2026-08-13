"""Provider fal.ai — accès à des modèles vidéo réalistes (Kling, Luma, Wan, LTX).

fal offre des crédits gratuits à l'inscription, ce qui permet de tester des
modèles de haute qualité sans budget initial.
Docs : https://fal.ai/models  |  Clé : https://fal.ai/dashboard/keys
"""
from __future__ import annotations

import asyncio

import httpx

from ..config import get_settings
from ..models import Job
from .base import VideoProvider

# Ratio -> résolution indicative (certains modèles acceptent aspect_ratio direct).
_QUEUE_BASE = "https://queue.fal.run"


class FalProvider(VideoProvider):
    id = "fal"
    name = "fal.ai"
    description = "Modèles vidéo SOTA (Kling, Luma Ray, Wan, LTX). Crédits gratuits à l'inscription."
    free = True  # crédits offerts, sans carte
    requires_key = "FAL_KEY"
    models = [
        "fal-ai/ltx-video",            # rapide, open-source, léger
        "fal-ai/kling-video/v1/standard/text-to-video",
        "fal-ai/luma-dream-machine",
        "fal-ai/wan-t2v",
    ]

    def is_available(self) -> bool:
        return bool(get_settings().fal_key)

    async def generate(self, job: Job) -> str:
        settings = get_settings()
        model = job.model or self.models[0]
        headers = {"Authorization": f"Key {settings.fal_key}"}
        payload = {
            "prompt": job.enhanced_prompt or job.prompt,
            "aspect_ratio": job.aspect_ratio,
        }
        if job.seed is not None:
            payload["seed"] = job.seed

        async with httpx.AsyncClient(timeout=60) as client:
            # 1) Soumission dans la file d'attente fal.
            resp = await client.post(f"{_QUEUE_BASE}/{model}", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            status_url = data["status_url"]
            response_url = data["response_url"]

            # 2) Polling jusqu'à complétion.
            for _ in range(180):  # ~6 min max
                await asyncio.sleep(2)
                s = await client.get(status_url, headers=headers)
                s.raise_for_status()
                status = s.json().get("status")
                if status == "COMPLETED":
                    break
                if status in {"FAILED", "ERROR"}:
                    raise RuntimeError(f"fal a échoué: {s.text}")
            else:
                raise TimeoutError("fal: délai dépassé")

            # 3) Récupération du résultat.
            r = await client.get(response_url, headers=headers)
            r.raise_for_status()
            result = r.json()

        # Le champ vidéo varie selon les modèles.
        video = result.get("video") or {}
        url = video.get("url") if isinstance(video, dict) else None
        if not url:
            # certains modèles renvoient une liste "videos"
            videos = result.get("videos") or []
            if videos and isinstance(videos[0], dict):
                url = videos[0].get("url")
        if not url:
            raise RuntimeError(f"fal: URL vidéo introuvable dans la réponse: {result}")
        return url
