"""Étape de clarification : dialogue avec le soumissionnaire → objet `Brief`.

C'est le contrat central du pipeline. À partir du document ingéré, on génère
un petit questionnaire ADAPTATIF (au type de document), on collecte les
réponses, puis on assemble un `Brief` typé que toutes les étapes suivantes
(storyboard, rendu) consommeront.

Deux modes, comme l'enhancer :
  - LLM (Claude/OpenAI) si clé présente → questions sur-mesure
  - fallback règle-based (gratuit, sans clé) → questions par profil de document
"""
from __future__ import annotations

import json
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from ..config import get_settings
from ..ingestion.schema import DocType, Document


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    #: propositions de réponses (l'UI peut aussi laisser un champ libre)
    options: list[str] = []
    #: réponse par défaut si le soumissionnaire ne choisit rien
    default: Optional[str] = None
    multi: bool = False


class Brief(BaseModel):
    """Intention de production, dérivée du document + des réponses."""
    document_id: str
    doc_type: DocType
    objective: Optional[str] = None       # informer, convaincre, vulgariser…
    audience: Optional[str] = None
    tone: Optional[str] = None            # sobre, dynamique, dramatique…
    language: str = "fr"
    duration_seconds: int = 60
    visual_style: Optional[str] = None
    voiceover: bool = True
    captions: bool = True
    # Spécifique BD
    character_voices: bool = False
    sound_effects: bool = False
    # Réponses brutes conservées pour traçabilité
    answers: dict[str, str] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Questions par défaut (fallback gratuit), communes puis spécifiques au type.
# --------------------------------------------------------------------------- #
_COMMON = [
    ClarificationQuestion(
        id="objective",
        question="Quel est l'objectif principal de la vidéo ?",
        options=["Informer / résumer", "Convaincre / vendre", "Vulgariser / expliquer", "Divertir"],
        default="Informer / résumer",
    ),
    ClarificationQuestion(
        id="audience",
        question="À qui s'adresse la vidéo ?",
        options=["Grand public", "Clients / prospects", "Interne / équipe", "Experts du domaine"],
        default="Grand public",
    ),
    ClarificationQuestion(
        id="duration",
        question="Durée cible ?",
        options=["30 s", "60 s", "2 min", "5 min"],
        default="60 s",
    ),
    ClarificationQuestion(
        id="tone",
        question="Quel ton visuel et narratif ?",
        options=["Sobre / corporate", "Dynamique / moderne", "Chaleureux", "Dramatique / cinéma"],
        default="Dynamique / moderne",
    ),
    ClarificationQuestion(
        id="language",
        question="Langue de la narration ?",
        options=["Français", "Anglais"],
        default="Français",
    ),
]

_BY_TYPE: dict[DocType, list[ClarificationQuestion]] = {
    DocType.COMIC: [
        ClarificationQuestion(
            id="comic_style",
            question="Quel style d'animation pour la BD ?",
            options=[
                "Motion comic (cases révélées une à une)",
                "Caméra qui voyage sur les planches",
                "Bulles qui apparaissent au rythme de la voix",
            ],
            default="Motion comic (cases révélées une à une)",
        ),
        ClarificationQuestion(
            id="character_voices",
            question="Faut-il des voix distinctes par personnage ?",
            options=["Oui, une voix par personnage", "Non, un seul narrateur"],
            default="Non, un seul narrateur",
        ),
        ClarificationQuestion(
            id="sound_effects",
            question="Ajouter des bruitages / ambiance sonore ?",
            options=["Oui", "Non"],
            default="Oui",
        ),
    ],
    DocType.SLIDES: [
        ClarificationQuestion(
            id="slide_mapping",
            question="Comment traiter les slides ?",
            options=["Une scène par slide", "Regrouper par thème", "Ne garder que l'essentiel"],
            default="Une scène par slide",
        ),
    ],
    DocType.SCIENTIFIC: [
        ClarificationQuestion(
            id="depth",
            question="Niveau de vulgarisation ?",
            options=["Fidèle et technique", "Vulgarisé grand public", "Intermédiaire"],
            default="Vulgarisé grand public",
        ),
    ],
    DocType.REPORT: [
        ClarificationQuestion(
            id="focus",
            question="Sur quoi mettre l'accent ?",
            options=["Chiffres clés", "Conclusions / recommandations", "Vue d'ensemble"],
            default="Conclusions / recommandations",
        ),
    ],
}


def _rule_based_questions(doc: Document) -> list[ClarificationQuestion]:
    return list(_BY_TYPE.get(doc.doc_type, [])) + _COMMON


_SYSTEM = (
    "Tu prépares la production d'une vidéo à partir d'un document. À partir du "
    "résumé fourni, génère un TRÈS COURT questionnaire (3 à 5 questions max) pour "
    "clarifier l'intention avec la personne qui a soumis le document. Adapte les "
    "questions au type de document. Réponds STRICTEMENT en JSON: une liste "
    "d'objets {id, question, options[], default, multi}. Pas de texte hors JSON."
)


async def _llm_questions(doc: Document) -> list[ClarificationQuestion]:
    settings = get_settings()
    mode = settings.prompt_enhancer.lower()
    payload_msg = doc.summary()

    if mode == "anthropic" and settings.anthropic_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-5",
                    "max_tokens": 800,
                    "system": _SYSTEM,
                    "messages": [{"role": "user", "content": payload_msg}],
                },
            )
            r.raise_for_status()
            raw = r.json()["content"][0]["text"]
    elif mode == "openai" and settings.openai_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 800,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": payload_msg},
                    ],
                },
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError("Pas de clé LLM configurée")

    # Extraction robuste du JSON (accepte objet {questions:[...]} ou liste nue).
    start = raw.find("[")
    obj_start = raw.find("{")
    data = json.loads(raw[start:] if 0 <= start < obj_start or obj_start == -1 else raw)
    items = data["questions"] if isinstance(data, dict) else data
    return [ClarificationQuestion(**q) for q in items]


async def generate_questions(doc: Document) -> list[ClarificationQuestion]:
    """Questions de clarification, adaptées au document. Ne lève jamais :
    en cas d'échec LLM, retombe sur le questionnaire règle-based (gratuit)."""
    try:
        return await _llm_questions(doc)
    except Exception:
        return _rule_based_questions(doc)


# --------------------------------------------------------------------------- #
# Assemblage du Brief à partir des réponses.
# --------------------------------------------------------------------------- #
def _duration_to_seconds(value: str | None) -> int:
    if not value:
        return 60
    v = value.lower()
    if "30" in v:
        return 30
    if "5" in v and "min" in v:
        return 300
    if "2" in v and "min" in v:
        return 120
    return 60


def build_brief(doc: Document, answers: dict[str, str]) -> Brief:
    lang = "en" if str(answers.get("language", "")).lower().startswith(("en", "angl")) else "fr"
    return Brief(
        document_id=doc.id,
        doc_type=doc.doc_type,
        objective=answers.get("objective"),
        audience=answers.get("audience"),
        tone=answers.get("tone"),
        language=lang,
        duration_seconds=_duration_to_seconds(answers.get("duration")),
        visual_style=answers.get("comic_style") or answers.get("tone"),
        character_voices=str(answers.get("character_voices", "")).lower().startswith(("oui", "yes")),
        sound_effects=str(answers.get("sound_effects", "")).lower().startswith(("oui", "yes")),
        answers=answers,
    )
