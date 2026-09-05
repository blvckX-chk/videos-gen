"""Provider eSpeak NG — TTS 100 % offline, gratuit, sans modèle à télécharger.

Qualité robotique : sert de socle de test bout-en-bout et de filet de sécurité
quand Kokoro n'est pas disponible. Sur le VPS on privilégiera Kokoro.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from .base import TTSProvider

_LANG_MAP = {"fr": "fr", "en": "en-us"}


class EspeakProvider(TTSProvider):
    id = "espeak"
    name = "eSpeak NG"
    description = "TTS offline gratuit (qualité basique). Aucun modèle requis."
    free = True
    requires_key = None
    voices = ["fr", "en"]

    def is_available(self) -> bool:
        return shutil.which("espeak-ng") is not None

    async def synthesize(self, text: str, out_path: Path,
                         voice: str | None = None, lang: str = "fr") -> Path:
        v = _LANG_MAP.get(lang, "fr")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # -s : vitesse (mots/min), -p : pitch, -w : sortie WAV
        proc = await asyncio.create_subprocess_exec(
            "espeak-ng", "-v", v, "-s", "165", "-p", "45",
            "-w", str(out_path), text,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0 or not out_path.exists():
            raise RuntimeError(f"espeak-ng a échoué : {err[-300:].decode(errors='replace')}")
        return out_path
