"""Amélioration de prompt : le levier n°1 du réalisme, et il est gratuit.

Les modèles vidéo produisent des résultats bien plus réalistes quand le prompt
décrit précisément la caméra, l'objectif, la lumière, le matériau, le mouvement
et l'ambiance. Ce module transforme un prompt simple en prompt « cinéma ».

Trois modes (config `PROMPT_ENHANCER`) :
  - rule_based : gratuit, sans clé, déterministe (défaut)
  - anthropic  : via l'API Claude (meilleure qualité) si ANTHROPIC_API_KEY
  - openai     : via l'API OpenAI si OPENAI_API_KEY
"""
from __future__ import annotations

import httpx

from ..config import get_settings

# Descripteurs qui poussent les modèles vers le photoréalisme.
_CINEMATIC_TAGS = [
    "photorealistic",
    "shot on ARRI Alexa 35, 35mm anamorphic lens",
    "shallow depth of field, natural bokeh",
    "cinematic color grading",
    "soft volumetric lighting, golden hour",
    "ultra-detailed textures, subsurface scattering on skin",
    "subtle camera movement, handheld micro-jitter",
    "high dynamic range, film grain",
    "8k, sharp focus",
]

_SYSTEM_PROMPT = (
    "Tu es un directeur de la photographie. On te donne une idée de vidéo courte. "
    "Réécris-la en UN SEUL paragraphe dense en anglais, optimisé pour un modèle "
    "text-to-video, afin d'obtenir le rendu le plus PHOTORÉALISTE possible. "
    "Précise : sujet et action, mouvement de caméra, type d'objectif et de plan, "
    "lumière et ambiance, matériaux et textures, palette de couleurs, heure/lieu. "
    "N'invente pas de dialogues. Ne mets pas de listes ni de préambule, seulement "
    "le prompt final."
)


def _rule_based(prompt: str) -> str:
    base = prompt.strip().rstrip(".")
    tags = ", ".join(_CINEMATIC_TAGS)
    return f"{base}. {tags}."


async def _anthropic(prompt: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-5",
                "max_tokens": 400,
                "system": _SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        data = r.json()
        return data["content"][0]["text"].strip()


async def _openai(prompt: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "max_tokens": 400,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()


async def enhance_prompt(prompt: str) -> str:
    """Renvoie une version enrichie du prompt. Ne lève jamais : en cas d'erreur
    LLM, on retombe sur la version règle-based (gratuite)."""
    settings = get_settings()
    mode = settings.prompt_enhancer.lower()
    try:
        if mode == "anthropic" and settings.anthropic_api_key:
            return await _anthropic(prompt, settings.anthropic_api_key)
        if mode == "openai" and settings.openai_api_key:
            return await _openai(prompt, settings.openai_api_key)
    except Exception:
        # Dégradation gracieuse vers le mode gratuit.
        pass
    return _rule_based(prompt)
