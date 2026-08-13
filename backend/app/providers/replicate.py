"""Provider Replicate — catalogue de modèles vidéo open-source hébergés.

Replicate offre des crédits gratuits et facture à la seconde de calcul.
Docs : https://replicate.com/collections/text-to-video
Token : https://replicate.com/account/api-tokens
"""
from __future__ import annotations

import asyncio

import httpx

from ..config import get_settings
from ..models import Job
from .base import VideoProvider

_API = "https://api.replicate.com/v1"


class ReplicateProvider(VideoProvider):
    id = "replicate"
    name = "Replicate"
    description = "Modèles vidéo open-source hébergés (Wan, LTX, Hunyuan). Crédits gratuits au départ."
    free = True
    requires_key = "REPLICATE_API_TOKEN"
    # Sur Replicate on cible un modèle par "owner/name"; la dernière version est
    # résolue automatiquement à l'exécution.
    models = [
        "wan-video/wan-2.1-1.3b",
        "lightricks/ltx-video",
        "tencent/hunyuan-video",
    ]

    def is_available(self) -> bool:
        return bool(get_settings().replicate_api_token)

    async def _latest_version(self, client: httpx.AsyncClient, model: str) -> str:
        r = await client.get(f"{_API}/models/{model}")
        r.raise_for_status()
        return r.json()["latest_version"]["id"]

    async def generate(self, job: Job) -> str:
        settings = get_settings()
        model = job.model or self.models[0]
        headers = {
            "Authorization": f"Bearer {settings.replicate_api_token}",
            "Content-Type": "application/json",
        }
        prompt = job.enhanced_prompt or job.prompt
        payload = {
            "input": {
                "prompt": prompt,
                "aspect_ratio": job.aspect_ratio,
            }
        }
        if job.seed is not None:
            payload["input"]["seed"] = job.seed

        async with httpx.AsyncClient(timeout=60) as client:
            version = await self._latest_version(client, model)
            payload["version"] = version

            resp = await client.post(f"{_API}/predictions", headers=headers, json=payload)
            resp.raise_for_status()
            pred = resp.json()
            get_url = pred["urls"]["get"]

            for _ in range(240):  # ~8 min max
                await asyncio.sleep(2)
                p = await client.get(get_url, headers=headers)
                p.raise_for_status()
                pred = p.json()
                if pred["status"] == "succeeded":
                    break
                if pred["status"] in {"failed", "canceled"}:
                    raise RuntimeError(f"Replicate a échoué: {pred.get('error')}")
            else:
                raise TimeoutError("Replicate: délai dépassé")

        output = pred.get("output")
        if isinstance(output, list):
            output = output[-1] if output else None
        if not output:
            raise RuntimeError(f"Replicate: sortie vidéo introuvable: {pred}")
        return output
