"""Génération de copy publicitaire natif par plateforme.

Deux modes (comme partout) :
  - `rule_based` : gratuit, sans clé, déterministe — s'appuie sur les points
    clés du document / l'intention + des gabarits par plateforme ;
  - `anthropic` / `openai` : copy rédigé par un LLM avec repli automatique.

Chaque plateforme a ses codes (longueur, ton, style de CTA, hashtags).
"""
from __future__ import annotations

import json
import re

import httpx

from ..config import get_settings
from ..services.documents import get_document
from ..storyboard import textutils as tx
from .schema import CopyRequest, CopyResult, CopyVariant, Platform, PlatformCopy

# --------------------------------------------------------------------------- #
# Codes par plateforme (pilotent le mode gratuit ET le prompt LLM)
# --------------------------------------------------------------------------- #
PLATFORM_SPECS: dict[Platform, dict] = {
    Platform.TIKTOK: {
        "label": "TikTok",
        "tone": "direct, punchy, oral, un brin provoc",
        "cta": ["Regarde jusqu'au bout 👀", "Enregistre pour plus tard", "Dis-moi en commentaire"],
        "hashtags": 5, "hook_style": "question ou affirmation choc",
    },
    Platform.INSTAGRAM: {
        "label": "Instagram",
        "tone": "esthétique, inspirant, chaleureux",
        "cta": ["Enregistre ce post ✨", "Partage en story", "Lien en bio"],
        "hashtags": 8, "hook_style": "bénéfice émotionnel",
    },
    Platform.YOUTUBE_SHORTS: {
        "label": "YouTube Shorts",
        "tone": "curieux, informatif, rythmé",
        "cta": ["Abonne-toi pour la suite", "Regarde la vidéo complète"],
        "hashtags": 3, "hook_style": "promesse d'apprentissage",
    },
    Platform.FACEBOOK: {
        "label": "Facebook",
        "tone": "accessible, communautaire, un peu plus long",
        "cta": ["En savoir plus", "Contacte-nous", "Partage autour de toi"],
        "hashtags": 2, "hook_style": "histoire ou question proche",
    },
    Platform.LINKEDIN: {
        "label": "LinkedIn",
        "tone": "professionnel, crédible, orienté valeur",
        "cta": ["Ton avis en commentaire ?", "Parlons-en", "Découvre notre approche"],
        "hashtags": 3, "hook_style": "constat de marché ou insight",
    },
    Platform.META_AD: {
        "label": "Publicité Meta",
        "tone": "orienté conversion, bénéfice clair, preuve",
        "cta": ["Profites-en maintenant", "Commande aujourd'hui", "Essaie gratuitement"],
        "hashtags": 0, "hook_style": "douleur → solution",
    },
}


def _context(req: CopyRequest) -> tuple[str, list[str], str]:
    """Renvoie (titre, points_clés, thème) depuis le document ou l'intention."""
    if req.document_id:
        doc = get_document(req.document_id)
        if doc is not None:
            title = doc.title_guess or "Notre sujet"
            text = " ".join(p.text for p in doc.pages[:6])
            points = tx.key_points(text, limit=4) or [title]
            return title, points, title
    intent = (req.intent or "Notre offre").strip()
    return intent[:70], [intent], intent


def _hashtags(theme: str, n: int) -> list[str]:
    if n <= 0:
        return []
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", theme.lower())
    base = ["blvckunlimited"] + [w for w in words][:n]
    seen, out = set(), []
    for w in base:
        if w not in seen:
            seen.add(w)
            out.append("#" + w)
        if len(out) >= max(1, n):
            break
    return out


# --------------------------------------------------------------------------- #
# Mode règle-based (gratuit)
# --------------------------------------------------------------------------- #
def _rule_based(req: CopyRequest) -> CopyResult:
    title, points, theme = _context(req)
    tone = req.tone
    result = CopyResult(generator="rule_based")

    for plat in req.platforms:
        spec = PLATFORM_SPECS[plat]
        variants: list[CopyVariant] = []
        for i in range(max(1, req.variants)):
            label = chr(ord("A") + i)
            pt = points[i % len(points)]
            other = points[(i + 1) % len(points)]
            # Accroche selon le style de la plateforme
            if plat == Platform.META_AD:
                hook = f"Marre de {theme.lower()} sans résultat ?"
            elif plat == Platform.LINKEDIN:
                hook = f"{title} : ce que personne ne dit."
            elif plat in (Platform.TIKTOK, Platform.YOUTUBE_SHORTS):
                hook = f"Tu savais ça sur {title.lower()} ?" if i == 0 else f"Stop. {title}, en 15 secondes."
            else:
                hook = f"{title} — l'essentiel." if i == 0 else f"On te résume {title.lower()}."
            body = tx.shorten(pt, 180)
            if plat in (Platform.FACEBOOK, Platform.LINKEDIN):
                body = tx.shorten(f"{pt} {other}" if other != pt else pt, 280)
            cta = spec["cta"][i % len(spec["cta"])]
            variants.append(CopyVariant(
                label=label, hook=hook, body=body, cta=cta,
                hashtags=_hashtags(theme, spec["hashtags"]),
            ))
        result.platforms.append(PlatformCopy(platform=plat, variants=variants))
    return result


# --------------------------------------------------------------------------- #
# Mode LLM
# --------------------------------------------------------------------------- #
def _llm_prompt(req: CopyRequest) -> str:
    title, points, theme = _context(req)
    specs = "\n".join(
        f"- {PLATFORM_SPECS[p]['label']} ({p.value}) : ton {PLATFORM_SPECS[p]['tone']}, "
        f"CTA style {PLATFORM_SPECS[p]['cta'][0]}, {PLATFORM_SPECS[p]['hashtags']} hashtags"
        for p in req.platforms
    )
    tone = req.tone or "à adapter par plateforme"
    return (
        f"SUJET : {title}\nPOINTS CLÉS : {points}\nTON DE MARQUE : {tone}\n"
        f"LANGUE : {req.language}\nVARIANTES par plateforme : {req.variants}\n\n"
        f"PLATEFORMES :\n{specs}"
    )


_SYSTEM = (
    "Tu es copywriter publicitaire. Écris un copy NATIF par plateforme (le ton "
    "diffère fortement de l'une à l'autre), en variantes A/B. Chaque variante : "
    "une accroche scroll-stop, un corps court, un CTA adapté, des hashtags. "
    "Réponds STRICTEMENT en JSON: {\"platforms\":[{\"platform\":\"<id>\","
    "\"variants\":[{\"label\":\"A\",\"hook\":str,\"body\":str,\"cta\":str,"
    "\"hashtags\":[str]}]}]}. Pas de texte hors JSON."
)


async def _llm(req: CopyRequest) -> CopyResult:
    settings = get_settings()
    mode = settings.prompt_enhancer.lower()
    prompt = _llm_prompt(req)

    if mode == "anthropic" and settings.anthropic_api_key:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key,
                         "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-5", "max_tokens": 1800,
                      "system": _SYSTEM, "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            raw = r.json()["content"][0]["text"]
    elif mode == "openai" and settings.openai_api_key:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}",
                         "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "max_tokens": 1800,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": _SYSTEM},
                                   {"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError("Pas de clé LLM configurée")

    data = json.loads(raw[raw.find("{"):])
    result = CopyResult(generator=mode)
    for pc in data.get("platforms", []):
        try:
            plat = Platform(pc["platform"])
        except (ValueError, KeyError):
            continue
        variants = [CopyVariant(**v) for v in pc.get("variants", [])]
        if variants:
            result.platforms.append(PlatformCopy(platform=plat, variants=variants))
    if not result.platforms:
        raise RuntimeError("copy LLM vide")
    return result


async def generate_copy(req: CopyRequest) -> CopyResult:
    """Génère le copy. Ne lève jamais : repli sur le mode gratuit."""
    # Ton de marque depuis la charte si fournie
    if req.charte_id and not req.tone:
        from ..identity.charters import get_charte
        c = get_charte(req.charte_id)
        if c is not None and c.tone:
            req.tone = c.tone
    try:
        return await _llm(req)
    except Exception:
        return _rule_based(req)
