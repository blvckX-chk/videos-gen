"""Client Tchavi — passerelle IA compatible OpenAI.

Une seule clé donne accès au catalogue (LLM, vision, image, vidéo, TTS,
musique, transcription). On parle directement HTTP plutôt que d'ajouter le SDK
OpenAI : moins de dépendances, et le contrôle des erreurs reste explicite.

Dégradation gracieuse : sans clé, `is_configured()` est faux et l'appelant
retombe sur son chemin déterministe.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

import httpx

from ..config import get_settings

logger = logging.getLogger("videos_gen.tchavi")

_TIMEOUT = httpx.Timeout(120.0)


def is_configured() -> bool:
    return bool(get_settings().tchavi_api_key)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_settings().tchavi_api_key}",
            "Content-Type": "application/json"}


def _url(path: str) -> str:
    return f"{get_settings().tchavi_base_url.rstrip('/')}/{path.lstrip('/')}"


async def list_models() -> list[dict[str, Any]]:
    """Catalogue des modèles disponibles (sert aussi de test de connectivité)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(_url("models"), headers=_headers())
        r.raise_for_status()
        data = r.json()
    return data.get("data", data if isinstance(data, list) else [])


async def chat(messages: list[dict[str, Any]], *, model: str | None = None,
               max_tokens: int = 2000, temperature: float = 0.4) -> str:
    """Complétion de chat. Renvoie le texte de la réponse."""
    payload = {
        "model": model or get_settings().tchavi_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(_url("chat/completions"), headers=_headers(), json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"Tchavi {r.status_code} : {r.text[:300]}")
        data = r.json()
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Réponse Tchavi inattendue : {str(data)[:300]}") from exc


def image_part(jpeg_bytes: bytes) -> dict[str, Any]:
    """Partie « image » d'un message multimodal, en data URL (rien n'est exposé
    publiquement : les photos ne transitent pas par une URL ouverte)."""
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    return {"type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def parse_json(text: str) -> Any:
    """Extrait le JSON d'une réponse, même entourée de texte ou de balises ```."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # dernier recours : le plus grand objet / tableau de la réponse
    for pattern in (r"\{.*\}", r"\[.*\]"):
        m = re.search(pattern, text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
    raise ValueError("Aucun JSON exploitable dans la réponse.")
