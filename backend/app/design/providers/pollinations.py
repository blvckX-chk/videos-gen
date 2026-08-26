"""Provider Pollinations — génération d'images gratuite, sans clé, sans compte.

C'est notre défaut pour le tier FREE. Endpoint public :
https://image.pollinations.ai/prompt/<url-encoded>?width=&height=&seed=&nologo=true
"""
from __future__ import annotations

import io
from urllib.parse import quote

import httpx
from PIL import Image

from .base import ImageProvider


class PollinationsProvider(ImageProvider):
    id = "pollinations"
    name = "Pollinations"
    description = "Génération d'images gratuite sans clé (défaut du tier free)."
    free = True
    requires_key = None
    models = ["flux", "flux-realism", "flux-anime", "flux-3d", "any-dark"]

    def is_available(self) -> bool:
        return True  # endpoint public sans auth

    async def generate(
        self, prompt: str, width: int, height: int,
        model: str | None = None, seed: int | None = None,
    ) -> Image.Image:
        model = model or self.models[0]
        params = {"width": width, "height": height, "nologo": "true", "model": model}
        if seed is not None:
            params["seed"] = seed
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
