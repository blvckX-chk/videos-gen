"""Planner du super-agent unifié.

Reçoit une intention + un document ingéré (optionnel) + un tier, et produit
un `Campaign` : une séquence typée d'étapes qui, une fois exécutées,
donnent tous les livrables d'une campagne SMM (Reel + posts + stories +
thumbnail…).

Deux modes (comme partout dans le système) :
  - `rule_based` (gratuit, sans clé, déterministe) — s'appuie sur le type
    de document et son contenu extrait au Slice 1 ;
  - `anthropic` / `openai` — LLM avec repli automatique.

Garde-fou blueprint v1.1 : un plan `free` ne planifie QUE des étapes
utilisables gratuitement (templates + Pollinations + Remotion local).
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from ..config import get_settings
from ..design.agent import _extract_stats  # même heuristique que l'agent design
from ..design.schema import ImageFormat
from ..ingestion.schema import DocType, Document
from ..models import Tier
from ..services.documents import get_document
from ..storyboard import textutils as tx
from .schema import Campaign, CampaignStep, DeliverableKind, StepType


# --------------------------------------------------------------------------- #
# Mode règle-based (défaut)
# --------------------------------------------------------------------------- #
def _wants_video(intent: str) -> bool:
    return bool(re.search(r"(vid[eé]o|reel|tiktok|shorts|clip)", intent, re.I))


def _wants_poster(intent: str) -> bool:
    return bool(re.search(r"(affiche|poster|banni[eè]re|flyer)", intent, re.I))


def _campaign_size(intent: str) -> int:
    """Petite heuristique : « une série », « campagne complète »… → plus d'étapes."""
    intent_l = intent.lower()
    if any(w in intent_l for w in ("compl", "s[eé]rie", "campagne", "carrou", "kit")):
        return 6
    if any(w in intent_l for w in ("plusieurs", "quelques", "3", "4", "5")):
        return 4
    return 3


def _rule_based_steps(intent: str, doc: Document | None, tier: Tier) -> list[CampaignStep]:
    steps: list[CampaignStep] = []
    size = _campaign_size(intent)

    # ---- Cas 1 : pas de document — on suit l'intention seule ----
    if doc is None:
        # Une génération d'illustration principale (post carré)
        steps.append(CampaignStep(
            type=StepType.IMAGE_GENERATE, kind=DeliverableKind.IMAGE,
            label="Visuel principal",
            prompt=intent, provider="pollinations",
            image_format=ImageFormat.SQUARE,
            rationale="Aucun document — génération directe depuis l'intention.",
        ))
        # Décliner en story si campagne demande du volume
        if size >= 4:
            steps.append(CampaignStep(
                type=StepType.IMAGE_GENERATE, kind=DeliverableKind.IMAGE,
                label="Story vertical",
                prompt=intent, provider="pollinations",
                image_format=ImageFormat.STORY,
                rationale="Format story pour couvrir IG/FB.",
            ))
        if _wants_video(intent):
            steps.append(CampaignStep(
                type=StepType.VIDEO_STORYBOARD, kind=DeliverableKind.VIDEO,
                label="Vidéo courte 30s",
                duration_seconds=30, video_aspect="9:16",
                focus=intent,
                rationale="Reel demandé dans l'intention.",
            ))
        return steps

    # ---- Cas 2 : avec document — mix riche ----
    title = doc.title_guess or "Le document"
    all_text = " ".join(p.text for p in doc.pages[:8])
    key_points = tx.key_points(all_text, limit=5)
    stats = _extract_stats(all_text, limit=2)

    # a) Un Reel 9:16 en tête de campagne (utilise le générateur de storyboard)
    is_comic = doc.doc_type == DocType.COMIC or bool(getattr(doc, "panels", None))
    steps.append(CampaignStep(
        type=StepType.VIDEO_STORYBOARD, kind=DeliverableKind.VIDEO,
        label=("Motion comic 30s" if is_comic else "Reel de synthèse 30s"),
        duration_seconds=30, video_aspect="9:16",
        tone="dynamique", focus=title,
        rationale=("BD → motion comic" if is_comic
                   else "Résumé animé du document en vertical court."),
    ))

    # b) Post carré de résumé (utile partout)
    if key_points and not is_comic:
        steps.append(CampaignStep(
            type=StepType.IMAGE_TEMPLATE, kind=DeliverableKind.IMAGE,
            label="Post résumé",
            template="summary_card",
            params={"title": title, "bullets": key_points[:4],
                    "subtitle": doc.doc_type.value, "format": "square"},
            image_format=ImageFormat.SQUARE,
            rationale=f"Synthèse en {min(4, len(key_points))} points.",
        ))

    # c) Une ou deux quote cards pour les meilleures phrases
    for pt in key_points[:2]:
        steps.append(CampaignStep(
            type=StepType.IMAGE_TEMPLATE, kind=DeliverableKind.IMAGE,
            label=f"Citation : {tx.shorten(pt, 40)}",
            template="quote_card",
            params={"text": pt, "author": title, "format": "square"},
            image_format=ImageFormat.SQUARE,
            rationale="Point-clé transformé en citation partageable.",
        ))

    # d) Cartes chiffre-clé
    for num, ctx in stats:
        steps.append(CampaignStep(
            type=StepType.IMAGE_TEMPLATE, kind=DeliverableKind.IMAGE,
            label=f"Chiffre : {num}",
            template="stat_card",
            params={"number": num, "label": "chiffre-clé",
                    "context": ctx, "format": "square"},
            image_format=ImageFormat.SQUARE,
            rationale=f"Mise en avant du chiffre « {num} ».",
        ))

    # e) Story vertical déclinée du résumé (si campagne demande du volume)
    if size >= 5 and key_points:
        steps.append(CampaignStep(
            type=StepType.IMAGE_TEMPLATE, kind=DeliverableKind.IMAGE,
            label="Story de résumé",
            template="summary_card",
            params={"title": title, "bullets": key_points[:3],
                    "subtitle": doc.doc_type.value, "format": "story"},
            image_format=ImageFormat.STORY,
            rationale="Story vertical alignée avec les Reels.",
        ))

    # f) Affiche/poster si demandé
    if _wants_poster(intent) or is_comic:
        steps.append(CampaignStep(
            type=StepType.IMAGE_GENERATE, kind=DeliverableKind.IMAGE,
            label="Affiche verticale",
            prompt=(f"cinematic bold poster illustration, dramatic lighting, {title}"),
            provider="pollinations",
            image_format=ImageFormat.STORY,
            rationale="Affiche générée pour animation/promotion.",
        ))

    # g) Thumbnail YouTube si volume ≥ 4
    if size >= 4:
        thumb_text = tx.shorten(title, 40)
        steps.append(CampaignStep(
            type=StepType.IMAGE_TEMPLATE, kind=DeliverableKind.IMAGE,
            label="Thumbnail YouTube",
            template="quote_card",
            params={"text": thumb_text, "author": "blvckUnlimited", "format": "landscape"},
            image_format=ImageFormat.LANDSCAPE,
            rationale="Miniature 16:9 pour la version longue.",
        ))

    # Filtre tier free (garde-fou v1.1)
    if tier == Tier.FREE:
        steps = [s for s in steps if s.type != StepType.IMAGE_GENERATE
                 or s.provider == "pollinations"]

    return steps or _rule_based_steps(intent, None, tier)  # fallback


# --------------------------------------------------------------------------- #
# Mode LLM (Claude / OpenAI)
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "Tu es directeur de la communication. À partir d'une INTENTION et d'un "
    "RÉSUMÉ éventuel de document, planifie une CAMPAGNE MULTI-MODALITÉS "
    "pour les réseaux sociaux (mix vidéo + images). "
    "Types d'étapes disponibles : "
    "1) image_template (templates: quote_card, stat_card, summary_card, product_card) "
    "2) image_generate (provider `pollinations` gratuit) "
    "3) video_storyboard (Reel court, 15-60s). "
    "Réponds STRICTEMENT en JSON: {\"steps\":[{\"type\":str, \"kind\":\"image\"|\"video\", "
    "\"label\":str, \"template\":str|null, \"params\":object, \"prompt\":str|null, "
    "\"provider\":str|null, \"image_format\":\"square\"|\"story\"|\"landscape\", "
    "\"duration_seconds\":int, \"video_aspect\":\"9:16\"|\"1:1\"|\"16:9\", "
    "\"tone\":str|null, \"focus\":str|null, \"rationale\":str}]}. "
    "3 à 6 étapes max, campagne cohérente. Pas de texte hors JSON."
)


async def _llm_steps(intent: str, doc: Document | None, tier: Tier) -> list[CampaignStep]:
    settings = get_settings()
    mode = settings.prompt_enhancer.lower()
    payload = f"INTENTION : {intent}\n"
    if doc is not None:
        payload += f"\nDOCUMENT :\n{doc.summary(2000)}"

    if mode == "anthropic" and settings.anthropic_api_key:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key,
                         "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-5", "max_tokens": 1600,
                      "system": _SYSTEM, "messages": [{"role": "user", "content": payload}]},
            )
            r.raise_for_status()
            raw = r.json()["content"][0]["text"]
    elif mode == "openai" and settings.openai_api_key:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}",
                         "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "max_tokens": 1600,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": _SYSTEM},
                                   {"role": "user", "content": payload}]},
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError("Pas de clé LLM configurée")

    obj_start = raw.find("{")
    data = json.loads(raw[obj_start:])
    steps: list[CampaignStep] = []
    for s in data.get("steps", []):
        try:
            steps.append(CampaignStep(**s))
        except Exception:
            continue

    if tier == Tier.FREE:
        steps = [s for s in steps if s.type != StepType.IMAGE_GENERATE
                 or s.provider == "pollinations"]
    if not steps:
        raise RuntimeError("Plan LLM vide après filtrage.")
    return steps


# --------------------------------------------------------------------------- #
# Entrée publique
# --------------------------------------------------------------------------- #
async def plan_campaign(intent: str, document_id: str | None = None,
                        tier: Tier = Tier.FREE) -> Campaign:
    doc = get_document(document_id) if document_id else None
    campaign = Campaign(intent=intent, document_id=document_id, tier=tier)
    try:
        campaign.steps = await _llm_steps(intent, doc, tier)
        campaign.generator = get_settings().prompt_enhancer.lower()
    except Exception:
        campaign.steps = _rule_based_steps(intent, doc, tier)
        campaign.generator = "rule_based"
    return campaign
