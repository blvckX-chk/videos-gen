"""Génération du storyboard à partir du Brief + Document.

Deux modes (comme les autres services) :
  - rule_based : gratuit, sans clé, déterministe (défaut) ;
  - anthropic / openai : storyboard rédigé par un LLM si une clé est présente,
    avec repli automatique sur le mode règle-based en cas d'échec.

Le format vertical (9:16) est prioritaire : les durées et le nombre de shots
sont calibrés pour de la vidéo courte (Reels / TikTok / Shorts).
"""
from __future__ import annotations

import json

import httpx

from ..config import get_settings
from ..ingestion.schema import DocType, Document
from ..services.clarification import Brief
from . import textutils as tx
from .schema import Scene, Shot, ShotType, Storyboard

# Bornes de durée par shot (secondes) — rythme « vidéo courte ».
_MIN_SHOT = 2.0
_MAX_SHOT = 5.0
_TITLE_DUR = 2.5
_OUTRO_DUR = 2.5


def _distribute(target: float, n: int) -> float:
    """Durée par shot pour approcher la durée cible, bornée."""
    if n <= 0:
        return _MIN_SHOT
    d = target / n
    return round(max(_MIN_SHOT, min(_MAX_SHOT, d)), 2)


def _template_for(brief: Brief) -> str:
    return {
        DocType.COMIC: "motion_comic",
        DocType.SCIENTIFIC: "explainer",
        DocType.SLIDES: "deck",
        DocType.REPORT: "corporate",
    }.get(brief.doc_type, "default")


# --------------------------------------------------------------------------- #
# Mode règle-based (gratuit)
# --------------------------------------------------------------------------- #
def _comic_scenes(doc: Document, budget: float) -> list[Scene]:
    """Motion comic : une case par shot, dans l'ordre de lecture."""
    shots: list[Shot] = []
    idx = 0
    if doc.panels:
        panel_refs = [
            (pg.page_index, p.index)
            for pg in doc.panels
            for p in pg.panels
        ]
    else:
        # Pas encore segmenté : on retombe sur une planche par shot.
        panel_refs = [(p.index, None) for p in doc.pages]

    per = _distribute(budget, len(panel_refs) or 1)
    for page_i, panel_i in panel_refs:
        shots.append(Shot(
            index=idx,
            type=ShotType.PANEL if panel_i is not None else ShotType.PAGE,
            duration=per,
            source_page=page_i,
            source_panel=panel_i,
            transition_in="slide",
        ))
        idx += 1
    return [Scene(index=0, title="Planches", shots=shots)]


def _doc_scenes(doc: Document, budget: float, max_shots: int) -> list[Scene]:
    """Documents texte : titre de section + points clés par page."""
    scenes: list[Scene] = []
    shot_budget = max_shots
    scene_idx = 0
    for page in doc.pages:
        if shot_budget <= 0:
            break
        heading = tx.first_heading(page.text)
        points = tx.key_points(page.text, limit=2)
        if not heading and not points:
            continue
        shots: list[Shot] = []
        s_idx = 0
        for pt in points:
            if shot_budget <= 0:
                break
            shots.append(Shot(
                index=s_idx,
                type=ShotType.TEXT,
                text=tx.shorten(pt, 110),
                narration=pt,
                source_page=page.index,
            ))
            s_idx += 1
            shot_budget -= 1
        if shots:
            scenes.append(Scene(index=scene_idx, title=heading, shots=shots))
            scene_idx += 1
    return scenes


def _rule_based(doc: Document, brief: Brief) -> Storyboard:
    target = float(brief.duration_seconds)
    content_budget = max(target - _TITLE_DUR - _OUTRO_DUR, _MIN_SHOT)

    # Motion comic si c'est une BD OU si des cases ont déjà été segmentées.
    is_comic = brief.doc_type == DocType.COMIC or bool(doc.panels)
    if is_comic:
        scenes = _comic_scenes(doc, content_budget)
    else:
        # ~1 shot toutes les 3 s en moyenne pour du format court.
        max_shots = max(3, int(content_budget // 3))
        scenes = _doc_scenes(doc, content_budget, max_shots)
        # Recalibre les durées pour coller à la cible.
        total_shots = sum(len(s.shots) for s in scenes) or 1
        per = _distribute(content_budget, total_shots)
        for sc in scenes:
            for sh in sc.shots:
                sh.duration = per

    # Carton titre + outro encadrant les scènes.
    title = doc.title_guess or "Sans titre"
    intro = Scene(index=-1, title="Intro", shots=[Shot(
        index=0, type=ShotType.TITLE, duration=_TITLE_DUR,
        text=tx.shorten(title, 60), transition_in="fade",
    )])
    outro_text = "blvckUnlimited" if brief.tone else "Merci"
    outro = Scene(index=999, title="Outro", shots=[Shot(
        index=0, type=ShotType.OUTRO, duration=_OUTRO_DUR,
        text=outro_text, transition_in="fade",
    )])

    all_scenes = [intro] + scenes + [outro]
    for i, sc in enumerate(all_scenes):
        sc.index = i

    template = "motion_comic" if is_comic else _template_for(brief)
    return Storyboard(
        document_id=doc.id,
        language=brief.language,
        template=template,
        scenes=all_scenes,
        generator="rule_based",
    )


# --------------------------------------------------------------------------- #
# Mode LLM
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "Tu es monteur vidéo. À partir d'un document et d'un brief, produis un "
    "storyboard pour une vidéo COURTE et RYTHMÉE (format vertical 9:16, type "
    "Reels/TikTok). Réponds STRICTEMENT en JSON: "
    '{\"scenes\":[{\"title\":str,\"shots\":[{\"type\":\"title|text|page|panel|stat|quote|outro\",'
    '\"duration\":number,\"text\":str,\"narration\":str,\"source_page\":int|null}]}]}. '
    "Commence par un hook fort, termine par un call to action. Le texte à l'écran "
    "doit être court et percutant. Pas de texte hors JSON."
)


async def _llm(doc: Document, brief: Brief) -> Storyboard:
    settings = get_settings()
    mode = settings.prompt_enhancer.lower()
    prompt = (
        f"BRIEF: objectif={brief.objective}, audience={brief.audience}, ton={brief.tone}, "
        f"durée cible={brief.duration_seconds}s, langue={brief.language}.\n\n"
        f"DOCUMENT:\n{doc.summary(2500)}"
    )

    if mode == "anthropic" and settings.anthropic_api_key:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key,
                         "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-5", "max_tokens": 1500,
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
                json={"model": "gpt-4o-mini", "max_tokens": 1500,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": _SYSTEM},
                                   {"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
    else:
        raise RuntimeError("Pas de clé LLM configurée")

    start = raw.find("{")
    data = json.loads(raw[start:])
    scenes: list[Scene] = []
    for si, sc in enumerate(data.get("scenes", [])):
        shots = []
        for shi, sh in enumerate(sc.get("shots", [])):
            try:
                stype = ShotType(sh.get("type", "text"))
            except ValueError:
                stype = ShotType.TEXT
            shots.append(Shot(
                index=shi, type=stype,
                duration=float(sh.get("duration", 3.0)),
                text=sh.get("text"), narration=sh.get("narration"),
                source_page=sh.get("source_page"),
            ))
        scenes.append(Scene(index=si, title=sc.get("title"), shots=shots))
    if not scenes:
        raise RuntimeError("storyboard LLM vide")

    return Storyboard(
        document_id=doc.id, language=brief.language,
        template=_template_for(brief), scenes=scenes, generator=mode,
    )


async def generate_storyboard(doc: Document, brief: Brief) -> Storyboard:
    """Génère un storyboard. Ne lève jamais : repli sur le mode gratuit."""
    try:
        return await _llm(doc, brief)
    except Exception:
        return _rule_based(doc, brief)
