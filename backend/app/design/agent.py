"""Super-agent graphique : intention → plan de composition → assets.

Reçoit une intention en langage naturel + éventuellement un `document_id`
(un PDF déjà ingéré au Slice 1). Produit un **plan** typé : une liste
d'étapes que le service exécute.

Deux modes, mêmes règles que le reste du système :
  - `rule_based` : gratuit, sans clé, déterministe (défaut) — s'appuie sur
    le type de document et son contenu extrait
  - `anthropic` / `openai` : plan rédigé par un LLM avec repli automatique
    en cas d'échec

Le contrat blueprint v1.1 s'applique : sur un job `free`, l'agent ne planifie
QUE des étapes utilisant des providers `free=True` (ex : `pollinations`).
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal, Optional

import httpx
from pydantic import BaseModel, Field

from ..config import get_settings
from ..ingestion.schema import DocType, Document
from ..models import Tier
from ..services.documents import get_document
from ..storyboard import textutils as tx
from .schema import ImageFormat
from .templates import TEMPLATE_SPECS


StepType = Literal["template", "generate"]


class PlanStep(BaseModel):
    """Une étape du plan de l'agent — soit un template composé, soit une
    génération d'image via un provider."""
    type: StepType
    #: pour "template" : identifiant (`quote_card`, `stat_card`, …)
    template: Optional[str] = None
    #: paramètres du template ou du provider
    params: dict[str, Any] = Field(default_factory=dict)
    #: pour "generate" : prompt + provider
    prompt: Optional[str] = None
    provider: Optional[str] = None
    format: ImageFormat = ImageFormat.SQUARE
    #: raison lisible (traçabilité + debug)
    rationale: Optional[str] = None


class DesignPlan(BaseModel):
    intent: str
    document_id: Optional[str] = None
    tier: Tier = Tier.FREE
    generator: str = "rule_based"          # rule_based | anthropic | openai
    steps: list[PlanStep] = []


# --------------------------------------------------------------------------- #
# Mode règle-based (gratuit, sans clé)
# --------------------------------------------------------------------------- #
_STAT_PATTERN = re.compile(
    r"(?P<num>\d[\d\s.,]*\s*(?:%|k|K|M|MEUR|M€|€|\$|USD|EUR|CFA|FCFA)?)",
    re.UNICODE,
)


def _extract_stats(text: str, limit: int = 3) -> list[tuple[str, str]]:
    """Cherche des couples (chiffre, phrase courte englobante) dans le texte."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for sent in tx.sentences(text):
        if 3 <= len(sent.split()) <= 20:
            m = _STAT_PATTERN.search(sent)
            if m:
                num = m.group("num").strip()
                if num in seen or len(num) > 12:
                    continue
                seen.add(num)
                out.append((num, tx.shorten(sent, 100)))
                if len(out) >= limit:
                    break
    return out


def _rule_based_plan(intent: str, doc: Document | None, tier: Tier,
                     format: ImageFormat) -> list[PlanStep]:
    intent_l = intent.lower()
    steps: list[PlanStep] = []

    # Cas 1 — pas de document : on essaie de deviner via l'intention seule.
    if doc is None:
        # Si l'intention ressemble à une citation, on fait une quote card.
        m = re.search(r"['\"«]([^'\"»]{4,140})['\"»]", intent)
        if m:
            steps.append(PlanStep(
                type="template", template="quote_card", format=format,
                params={"text": m.group(1), "author": "blvckUnlimited",
                        "format": format.value},
                rationale="Citation détectée entre guillemets dans l'intention.",
            ))
        else:
            # Sinon : génération d'illustration à partir de l'intention.
            steps.append(PlanStep(
                type="generate", provider="pollinations", format=format,
                prompt=intent, rationale="Aucun document — génération directe.",
            ))
        return steps

    # Cas 2 — document présent : on compose selon son type + son contenu.
    title = doc.title_guess or "Document"
    all_text = " ".join(p.text for p in doc.pages[:6])
    key_points = tx.key_points(all_text, limit=5)
    stats = _extract_stats(all_text, limit=2)

    # a) Carte de résumé (toujours utile pour tout doc textuel)
    if key_points and doc.doc_type != DocType.COMIC:
        steps.append(PlanStep(
            type="template", template="summary_card", format=format,
            params={
                "title": title, "bullets": key_points[:4],
                "subtitle": doc.doc_type.value, "format": format.value,
            },
            rationale=f"Résumé du document — {len(key_points)} points clés extraits.",
        ))

    # b) Une carte chiffre-clé par stat trouvée
    for num, ctx in stats:
        steps.append(PlanStep(
            type="template", template="stat_card", format=format,
            params={
                "number": num, "label": "chiffre-clé", "context": ctx,
                "format": format.value,
            },
            rationale=f"Chiffre détecté : « {num} » — mise en avant.",
        ))

    # c) Une ou deux quote cards depuis les points forts
    for pt in key_points[:2]:
        steps.append(PlanStep(
            type="template", template="quote_card", format=format,
            params={"text": pt, "author": title, "format": format.value},
            rationale="Point-clé transformé en carte-citation.",
        ))

    # d) BD : on ajoute une génération d'affiche (si tier ≥ free et Pollinations OK)
    if doc.doc_type == DocType.COMIC:
        steps.append(PlanStep(
            type="generate", provider="pollinations", format=format,
            prompt=f"cinematic comic book poster, dramatic lighting, {title}",
            rationale="BD détectée — génération d'une affiche d'ambiance.",
        ))

    # Filtre tier free : ne garder que les étapes compatibles.
    if tier == Tier.FREE:
        steps = [s for s in steps if s.type == "template" or s.provider == "pollinations"]

    return steps or [PlanStep(
        type="generate", provider="pollinations", format=format, prompt=intent,
        rationale="Rien d'exploitable dans le document — fallback génération.",
    )]


# --------------------------------------------------------------------------- #
# Mode LLM (Claude / OpenAI)
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "Tu es directeur artistique. À partir d'une INTENTION utilisateur et d'un "
    "RÉSUMÉ éventuel de document, planifie 3 à 6 visuels pour les réseaux "
    "sociaux. Utilise ces templates disponibles : {templates}. "
    "Ou une génération d'image via provider `pollinations` (gratuit). "
    "Réponds STRICTEMENT en JSON: {\"steps\":[{\"type\":\"template\"|\"generate\", "
    "\"template\":str|null, \"params\":object, \"prompt\":str|null, "
    "\"provider\":str|null, \"format\":\"square\"|\"story\"|\"landscape\", "
    "\"rationale\":str}]}. Pas de texte hors JSON."
)


async def _llm_plan(intent: str, doc: Document | None, tier: Tier,
                    format: ImageFormat) -> list[PlanStep]:
    settings = get_settings()
    mode = settings.prompt_enhancer.lower()

    templates_desc = ", ".join(f"`{k}` ({v['label']})" for k, v in TEMPLATE_SPECS.items())
    system = _SYSTEM.format(templates=templates_desc)
    payload_msg = f"INTENTION : {intent}\nFORMAT : {format.value}\n"
    if doc is not None:
        payload_msg += f"\nDOCUMENT :\n{doc.summary(2000)}"

    if mode == "anthropic" and settings.anthropic_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key,
                         "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-5", "max_tokens": 1200,
                      "system": system, "messages": [{"role": "user", "content": payload_msg}]},
            )
            r.raise_for_status()
            raw = r.json()["content"][0]["text"]
    elif mode == "openai" and settings.openai_api_key:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}",
                         "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "max_tokens": 1200,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": payload_msg}]},
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError("Pas de clé LLM configurée")

    obj_start = raw.find("{")
    data = json.loads(raw[obj_start:])
    steps: list[PlanStep] = []
    for s in data.get("steps", []):
        try:
            steps.append(PlanStep(**s))
        except Exception:
            continue

    # Garde-fou tier free côté LLM (au cas où il proposerait un provider payant)
    if tier == Tier.FREE:
        steps = [s for s in steps if s.type == "template" or s.provider == "pollinations"]
    if not steps:
        raise RuntimeError("Plan LLM vide après filtrage.")
    return steps


# --------------------------------------------------------------------------- #
# Entrée publique
# --------------------------------------------------------------------------- #
async def plan(intent: str, document_id: str | None = None,
               tier: Tier = Tier.FREE,
               format: ImageFormat = ImageFormat.SQUARE) -> DesignPlan:
    """Compose un plan pour l'intention donnée. Ne lève jamais — repli
    déterministe si le LLM échoue ou est absent."""
    doc = get_document(document_id) if document_id else None

    plan_obj = DesignPlan(intent=intent, document_id=document_id, tier=tier)
    try:
        plan_obj.steps = await _llm_plan(intent, doc, tier, format)
        plan_obj.generator = get_settings().prompt_enhancer.lower()
    except Exception:
        plan_obj.steps = _rule_based_plan(intent, doc, tier, format)
        plan_obj.generator = "rule_based"
    return plan_obj
