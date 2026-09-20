"""Console conversationnelle KORA : routeur d'intention + dispatch.

Hybride (décision blueprint) : routage par **mots-clés gratuit** par défaut,
et compréhension fine par **LLM tool-calling** quand une clé est présente
(repli automatique sur le gratuit). Le chat ne réimplémente rien : il route
vers les modules existants (campagne, copy, design…) et renvoie un résultat
structuré que l'UI affiche dans le fil.
"""
from __future__ import annotations

import re

from ..copy.schema import CopyRequest, Platform
from ..copy.service import generate_copy
from ..campaign.planner import plan_campaign
from ..campaign.storage import save_campaign
from ..design.schema import ImageFormat
from ..design.templates import build_template
from ..design.composer import compose
from ..design.service import _asset_from_image
from ..design.schema import AssetKind
from ..models import Tier
from .schema import ChatRequest, ChatResponse, ChatResult

# --------------------------------------------------------------------------- #
# Détection d'intention (gratuite, mots-clés)
# --------------------------------------------------------------------------- #
_INTENTS = {
    "campaign": r"campagne|promouvoir|promo|lancer une campagne|plan de contenu",
    "copy": r"\bcopy\b|l[eé]gende|caption|accroche|texte du post|hashtags?|slogan",
    "card": r"carte|citation|chiffre[- ]cl[eé]|r[eé]sum[eé]|quote|stat",
    "image": r"image|visuel|affiche|poster|illustration|banni[eè]re|g[eé]n[eè]re? (une|un) ",
    "help": r"aide|que peux[- ]tu|capacit[eé]s|comment (ça|ca) marche|\bhelp\b",
}

_PLATFORM_WORDS = {
    Platform.TIKTOK: r"tiktok",
    Platform.INSTAGRAM: r"instagram|insta|ig\b",
    Platform.YOUTUBE_SHORTS: r"youtube|shorts?",
    Platform.FACEBOOK: r"facebook|fb\b",
    Platform.LINKEDIN: r"linkedin",
    Platform.META_AD: r"pub|ad\b|publicit[eé]|meta ad",
}

_FORMAT_WORDS = {
    ImageFormat.STORY: r"story|storie|vertical|9:16|affiche|poster",
    ImageFormat.LANDSCAPE: r"paysage|16:9|thumbnail|miniature|youtube",
    ImageFormat.SQUARE: r"carr[eé]|1:1|post",
}


def detect_intent(text: str) -> str:
    t = text.lower()
    for intent, pat in _INTENTS.items():
        if re.search(pat, t):
            return intent
    return "unknown"


def _platforms(text: str) -> list[Platform]:
    t = text.lower()
    found = [p for p, pat in _PLATFORM_WORDS.items() if re.search(pat, t)]
    return found or [Platform.TIKTOK, Platform.INSTAGRAM]


def _format(text: str) -> ImageFormat:
    t = text.lower()
    for fmt, pat in _FORMAT_WORDS.items():
        if re.search(pat, t):
            return fmt
    return ImageFormat.SQUARE


def _card_kind(text: str) -> str:
    t = text.lower()
    if re.search(r"chiffre|stat", t):
        return "stat_card"
    if re.search(r"r[eé]sum[eé]|summary", t):
        return "summary_card"
    return "quote_card"


def _strip_quotes(text: str) -> str | None:
    m = re.search(r"[«\"']([^»\"']{4,200})[»\"']", text)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# Dispatch (rule-based)
# --------------------------------------------------------------------------- #
async def _do_campaign(req: ChatRequest) -> ChatResponse:
    camp = await plan_campaign(req.message, req.document_id, Tier(req.tier))
    save_campaign(camp)
    n = len(camp.steps)
    return ChatResponse(
        reply=f"J'ai préparé un plan de campagne : {n} livrable(s). "
              f"Vérifie-le et clique « Lancer » pour l'exécuter.",
        intent="campaign", result=ChatResult(type="campaign_plan", data=camp.model_dump()),
    )


async def _do_copy(req: ChatRequest) -> ChatResponse:
    platforms = _platforms(req.message)
    res = await generate_copy(CopyRequest(
        intent=req.message, document_id=req.document_id,
        platforms=platforms, variants=2,
    ))
    labels = ", ".join(p.value for p in platforms)
    return ChatResponse(
        reply=f"Voici le copy (variantes A/B) pour : {labels}.",
        intent="copy", result=ChatResult(type="copy", data=res.model_dump()),
    )


async def _do_card(req: ChatRequest) -> ChatResponse:
    kind = _card_kind(req.message)
    fmt = _format(req.message)
    quote = _strip_quotes(req.message) or req.message.strip()[:120]
    if kind == "stat_card":
        params = {"number": "•••", "label": "chiffre-clé", "context": quote, "format": fmt.value}
    elif kind == "summary_card":
        params = {"title": quote[:60], "bullets": [quote], "format": fmt.value}
    else:
        params = {"text": quote, "author": "blvckUnlimited", "format": fmt.value}
    comp = build_template(kind, params)
    img = compose(comp)
    asset = _asset_from_image(img, name=f"chat — {kind}", kind=AssetKind.COMPOSED, format=fmt.value)
    return ChatResponse(
        reply=f"Carte générée ({kind.replace('_', ' ')}).",
        intent="card", result=ChatResult(type="image", data={"url": asset.url, "width": asset.width, "height": asset.height}),
    )


async def _do_image(req: ChatRequest) -> ChatResponse:
    # Génération IA = job asynchrone (provider Pollinations gratuit). L'UI poll.
    from ..design.service import run_generate_job
    from ..design.storage import save_job
    from ..design.schema import DesignJob
    fmt = _format(req.message)
    job = save_job(DesignJob(kind="generate"))
    import asyncio
    asyncio.create_task(run_generate_job(
        job.id, req.message, fmt.value, "pollinations", None, req.tier, None))
    return ChatResponse(
        reply="Je génère l'image… (elle apparaîtra dès qu'elle est prête).",
        intent="image", result=ChatResult(type="image_job", data={"job_id": job.id}),
    )


def _do_help() -> ChatResponse:
    return ChatResponse(
        reply=(
            "Je suis KORA. Dis-moi ce que tu veux, par exemple :\n"
            "• « Prépare une campagne complète pour promouvoir ce PDF »\n"
            "• « Écris le copy TikTok et LinkedIn pour ce lancement »\n"
            "• « Fais une carte citation : « La qualité ne se négocie pas » »\n"
            "• « Génère une affiche verticale pour un restaurant »\n"
            "Pour la retouche d'image, l'audio et la vidéo, utilise les onglets dédiés."
        ),
        intent="help", result=ChatResult(type="help"),
    )


async def handle_message(req: ChatRequest) -> ChatResponse:
    """Route et exécute un message. (Le chemin LLM tool-calling se branchera
    ici quand une clé est présente ; pour l'instant, routage gratuit.)"""
    intent = detect_intent(req.message)
    if intent == "campaign":
        return await _do_campaign(req)
    if intent == "copy":
        return await _do_copy(req)
    if intent == "card":
        return await _do_card(req)
    if intent == "image":
        return await _do_image(req)
    if intent == "help":
        return _do_help()
    # inconnu → aide guidée
    resp = _do_help()
    resp.reply = "Je n'ai pas bien saisi. " + resp.reply
    resp.intent = "unknown"
    return resp
