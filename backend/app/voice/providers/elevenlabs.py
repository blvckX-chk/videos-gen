"""Provider ElevenLabs — voix premium (accent africain francophone possible
via voice cloning). Payant → tier premium uniquement (répercuté au client).
"""
from __future__ import annotations

from pathlib import Path

import httpx

from ...config import get_settings
from .base import TTSProvider

# quelques voix multilingues par défaut (ids ElevenLabs publics courants)
_DEFAULT_VOICE = "EXAVITQu4vr4xnSDxMaL"  # "Sarah" — multilingue


class ElevenLabsProvider(TTSProvider):
    id = "elevenlabs"
    name = "ElevenLabs"
    description = "Voix premium multilingue, clonage possible (accent africain FR). Payant."
    free = False
    requires_key = "ELEVENLABS_API_KEY"
    voices = [_DEFAULT_VOICE]

    def is_available(self) -> bool:
        return bool(get_settings().elevenlabs_api_key)

    async def synthesize(self, text: str, out_path: Path,
                         voice: str | None = None, lang: str = "fr") -> Path:
        settings = get_settings()
        voice_id = voice or _DEFAULT_VOICE
        out_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                url,
                headers={"xi-api-key": settings.elevenlabs_api_key,
                         "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_multilingual_v2",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            )
            r.raise_for_status()
            out_path.write_bytes(r.content)
        return out_path

    def estimated_cost_cents(self, text: str) -> int:
        # ~ tarification au caractère ; estimation grossière (0.03 c/char)
        return max(1, round(len(text) * 0.03))
