"""Provider Piper TTS — voix off neuronale, gratuite, 100 % offline (CPU).

Bien plus naturel qu'eSpeak. Binaire autonome + modèle de voix installés dans
l'image Docker (voir Dockerfile). Voix FR féminine par défaut (siwis).
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from .base import TTSProvider

_BIN = os.environ.get("PIPER_BIN", "/opt/piper/piper")
# Modèle par langue (chemin .onnx). FR = voix féminine « siwis ».
_VOICES = {
    "fr": os.environ.get("PIPER_VOICE_FR", "/opt/piper/voices/fr_FR-siwis-medium.onnx"),
    "en": os.environ.get("PIPER_VOICE_EN", "/opt/piper/voices/en_US-amy-medium.onnx"),
}


class PiperProvider(TTSProvider):
    id = "piper"
    name = "Piper"
    description = "Voix off neuronale gratuite et offline (qualité naturelle)."
    free = True
    requires_key = None
    voices = ["fr", "en"]

    def _model_for(self, lang: str) -> str | None:
        path = _VOICES.get(lang) or _VOICES.get("fr")
        return path if path and Path(path).exists() else None

    def is_available(self) -> bool:
        return Path(_BIN).exists() and self._model_for("fr") is not None

    async def synthesize(self, text: str, out_path: Path,
                         voice: str | None = None, lang: str = "fr") -> Path:
        model = self._model_for(lang)
        if model is None:
            raise RuntimeError("Modèle Piper introuvable (voix non installée).")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Piper lit le texte sur stdin et écrit un WAV. LD_LIBRARY_PATH pour ses .so.
        env = {**os.environ, "LD_LIBRARY_PATH": str(Path(_BIN).parent)}
        proc = await asyncio.create_subprocess_exec(
            _BIN, "-m", model, "-f", str(out_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        _, err = await proc.communicate(text.encode("utf-8"))
        if proc.returncode != 0 or not out_path.exists():
            raise RuntimeError(f"Piper a échoué : {err[-300:].decode(errors='replace')}")
        return out_path
