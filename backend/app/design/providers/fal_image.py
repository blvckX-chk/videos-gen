"""Provider fal.ai pour la génération d'image (Flux, SDXL, etc.).

Utilise le compte fal existant (FAL_KEY) — crédits gratuits à l'inscription
puis facturation à l'usage sur le tier premium.
"""
from __future__ import annotations

import asyncio
import io

import httpx
from PIL import Image

from ...config import get_settings
from .base import ImageProvider

_QUEUE = "https://queue.fal.run"


class FalImageProvider(ImageProvider):
    id = "fal_image"
    name = "fal.ai (images)"
    description = "Flux, SDXL et autres modèles image via fal.ai. Crédits gratuits offerts."
    free = True  # crédits offerts, mais devient payant si consommé
    requires_key = "FAL_KEY"
    models = [
        "fal-ai/flux/schnell",
        "fal-ai/flux/dev",
        "fal-ai/flux-realism",
        "fal-ai/fast-sdxl",
    ]

    def is_available(self) -> bool:
        return bool(get_settings().fal_key)

    async def generate(
        self, prompt: str, width: int, height: int,
        model: str | None = None, seed: int | None = None,
    ) -> Image.Image:
        settings = get_settings()
        model = model or self.models[0]
        headers = {"Authorization": f"Key {settings.fal_key}"}
        payload: dict = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
        }
        if seed is not None:
            payload["seed"] = seed

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{_QUEUE}/{model}", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            status_url = data["status_url"]
            response_url = data["response_url"]

            for _ in range(120):
                await asyncio.sleep(1.5)
                s = await client.get(status_url, headers=headers)
                s.raise_for_status()
                st = s.json().get("status")
                if st == "COMPLETED":
                    break
                if st in {"FAILED", "ERROR"}:
                    raise RuntimeError(f"fal image a échoué : {s.text}")
            else:
                raise TimeoutError("fal image : délai dépassé")

            r2 = await client.get(response_url, headers=headers)
            r2.raise_for_status()
            result = r2.json()

        images = result.get("images") or []
        if not images or not isinstance(images[0], dict) or not images[0].get("url"):
            raise RuntimeError(f"fal image : sortie inattendue : {result}")

        async with httpx.AsyncClient(timeout=60) as c2:
            imgr = await c2.get(images[0]["url"])
            imgr.raise_for_status()
        return Image.open(io.BytesIO(imgr.content)).convert("RGBA")
