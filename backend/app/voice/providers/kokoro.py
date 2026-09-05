"""Provider Kokoro — TTS open-source de qualité (Apache-2.0), gratuit.

Kokoro (82M) tourne sur CPU en quasi-temps réel. Le modèle est téléchargé au
premier usage (~330 Mo) — potentiellement bloqué sur une infra à sortie
réseau restreinte (comme en dev ici). Sur le VPS il fonctionne normalement.

Import paresseux : l'indisponibilité de la lib ne casse pas le module voice.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from .base import TTSProvider

# Voix Kokoro (préfixe langue). Liste réduite aux plus utiles ici.
_VOICES = {
    "fr": "ff_siwis",
    "en": "af_heart",
}


class KokoroProvider(TTSProvider):
    id = "kokoro"
    name = "Kokoro"
    description = "TTS open-source de qualité, gratuit, offline (modèle ~330 Mo au 1er usage)."
    free = True
    requires_key = None
    voices = list(_VOICES.values())

    def is_available(self) -> bool:
        try:
            import kokoro  # type: ignore  # noqa: F401
            return True
        except Exception:
            return False

    async def synthesize(self, text: str, out_path: Path,
                         voice: str | None = None, lang: str = "fr") -> Path:
        if not self.is_available():
            raise RuntimeError("Kokoro non installé (`pip install kokoro soundfile`).")

        def _run() -> Path:
            import soundfile as sf  # type: ignore
            from kokoro import KPipeline  # type: ignore
            lang_code = "f" if lang == "fr" else "a"  # 'a' = anglais US
            pipe = KPipeline(lang_code=lang_code)
            v = voice or _VOICES.get(lang, "af_heart")
            audio_chunks = []
            for _, _, audio in pipe(text, voice=v):
                audio_chunks.append(audio)
            import numpy as np  # type: ignore
            data = np.concatenate(audio_chunks) if audio_chunks else np.zeros(1)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(out_path), data, 24000)
            return out_path

        # Kokoro est synchrone/CPU → on l'exécute hors de la boucle asyncio.
        return await asyncio.to_thread(_run)
