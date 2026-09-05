"""Registre des providers TTS. Ordre = préférence (premier dispo = défaut free)."""
from __future__ import annotations

from .base import TTSProvider
from .elevenlabs import ElevenLabsProvider
from .espeak import EspeakProvider
from .kokoro import KokoroProvider

_PROVIDERS: dict[str, TTSProvider] = {
    p.id: p for p in (
        KokoroProvider(),      # gratuit qualité (VPS)
        EspeakProvider(),      # gratuit offline (fallback / dev)
        ElevenLabsProvider(),  # premium
    )
}


def all_tts_providers() -> list[TTSProvider]:
    return list(_PROVIDERS.values())


def get_tts_provider(pid: str) -> TTSProvider | None:
    return _PROVIDERS.get(pid)


def default_free_tts() -> TTSProvider:
    for p in _PROVIDERS.values():
        if p.free and p.is_available():
            return p
    raise RuntimeError("Aucun provider TTS gratuit disponible (installe espeak-ng).")
