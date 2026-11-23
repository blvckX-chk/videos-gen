"""Tri puis curation : de 50 photos brutes à un scénario de montage.

Deux couches enchaînées :
1. **Déterministe** (gratuit, instantané) : écarte flou, ratés d'exposition et
   quasi-doublons, et note chaque photo.
2. **Curation par vision** (Tchavi, optionnelle) : choisit les meilleures parmi
   les rescapées et leur donne un **ordre narratif** + des titres.

Sans clé Tchavi, la couche 2 est sautée et la sélection reste celle de la
couche 1, en ordre chronologique — le système reste utilisable gratuitement.
"""
from __future__ import annotations

import io
import logging

from ..media import storage as media_store
from ..media.schema import MediaKind
from ..tchavi import client as tchavi
from .analyze import analyze_photo, apply_relative_sharpness, mark_duplicates
from .schema import PhotoAnalysis, Scenario, ScenarioClip

logger = logging.getLogger("videos_gen.curation")

#: Nombre d'images envoyées au modèle de vision (coût et latence bornés).
MAX_VISION_IMAGES = 30
#: Côté le plus long des vignettes envoyées au modèle.
VISION_THUMB = 384


def _photos(media_ids: list[str] | None) -> list:
    items = (
        [m for m in (media_store.get(i) for i in media_ids) if m is not None]
        if media_ids else media_store.list_items("photo")
    )
    photos = [m for m in items if m.kind == MediaKind.PHOTO]
    # ordre de l'album : du plus ancien au plus récent
    return sorted(photos, key=lambda m: m.created_at)


def analyze(media_ids: list[str] | None = None) -> list[PhotoAnalysis]:
    """Couche 1 : mesure et note chaque photo, repère les quasi-doublons."""
    photos = _photos(media_ids)
    analyses: list[PhotoAnalysis] = []
    hashes: list[int | None] = []
    for m in photos:
        path = media_store.media_path(m.id, m.ext)
        if not path.exists():
            continue
        a, h = analyze_photo(path, m.id)
        analyses.append(a)
        hashes.append(h)
    # Le flou s'apprécie par rapport à l'album avant d'écarter les doublons :
    # inutile de garder la « meilleure » d'une rafale si elle est floue.
    apply_relative_sharpness(analyses)
    mark_duplicates(analyses, hashes)
    return analyses


def _thumb_bytes(path, side: int = VISION_THUMB) -> bytes | None:
    """Vignette JPEG compacte pour l'envoi au modèle de vision."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((side, side))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=80)
            return buf.getvalue()
    except Exception:  # noqa: BLE001
        logger.warning("Vignette de vision impossible pour %s", path, exc_info=True)
        return None


async def _curate_with_vision(candidates: list, analyses: dict[str, PhotoAnalysis],
                              target: int, theme: str | None) -> dict | None:
    """Couche 2 : le modèle choisit et ordonne. None si indisponible."""
    subset = candidates[:MAX_VISION_IMAGES]
    content: list = [{
        "type": "text",
        "text": (
            f"Tu es monteur vidéo. Voici {len(subset)} photos numérotées de 0 à "
            f"{len(subset) - 1}, dans l'ordre chronologique de prise de vue.\n"
            f"Thème : {theme or 'reportage événementiel'}.\n\n"
            f"Sélectionne les {target} meilleures et range-les dans un ORDRE "
            "NARRATIF (ouverture, déroulé, moments forts, conclusion). Évite les "
            "redites visuelles. Donne un titre court (3 à 5 mots) uniquement aux "
            "plans qui en méritent un.\n\n"
            "Réponds UNIQUEMENT en JSON :\n"
            '{"rationale":"une phrase sur la logique du montage",'
            '"clips":[{"i":0,"title":"Titre ou null"}]}'
        ),
    }]
    for idx, m in enumerate(subset):
        thumb = _thumb_bytes(media_store.media_path(m.id, m.ext))
        if thumb is None:
            continue
        content.append({"type": "text", "text": f"Photo {idx}"})
        content.append(tchavi.image_part(thumb))

    try:
        raw = await tchavi.chat([{"role": "user", "content": content}],
                                max_tokens=2000, temperature=0.3)
        data = tchavi.parse_json(raw)
    except Exception as exc:  # noqa: BLE001 — on retombe sur le déterministe
        logger.warning("Curation Tchavi indisponible : %s", exc)
        return None

    clips = []
    seen = set()
    for entry in (data.get("clips") or []):
        try:
            i = int(entry.get("i"))
        except (TypeError, ValueError):
            continue
        if not (0 <= i < len(subset)) or i in seen:
            continue
        seen.add(i)
        title = entry.get("title")
        clips.append((subset[i].id, title if isinstance(title, str) and title.strip() else None))
    if not clips:
        return None
    return {"rationale": str(data.get("rationale") or ""), "clips": clips}


async def build_scenario(media_ids: list[str] | None = None, *,
                         target_count: int | None = None,
                         theme: str | None = None,
                         per_photo: float = 2.5) -> Scenario:
    """Chaîne complète : tri déterministe puis curation, et retourne un montage
    proposé (non enregistré) que l'utilisateur peut éditer."""
    analyses = analyze(media_ids)
    by_id = {a.media_id: a for a in analyses}
    photos = _photos(media_ids)

    kept = [m for m in photos if by_id.get(m.id) and by_id[m.id].keep]
    rejected = [a for a in analyses if not a.keep]

    if not kept:
        return Scenario(title="Montage", engine="rule_based",
                        rationale="Aucune photo exploitable (toutes floues ou en doublon).",
                        clips=[], rejected=rejected)

    target = target_count or min(len(kept), max(8, round(len(kept) * 0.6)))
    target = max(1, min(target, len(kept)))

    # Si trop de candidates pour la vision, on pré-réduit par la note.
    candidates = kept
    if len(candidates) > MAX_VISION_IMAGES:
        best = sorted(candidates, key=lambda m: by_id[m.id].score, reverse=True)
        best = best[:MAX_VISION_IMAGES]
        keep_ids = {m.id for m in best}
        candidates = [m for m in kept if m.id in keep_ids]   # ordre chronologique

    curated = None
    if tchavi.is_configured():
        curated = await _curate_with_vision(candidates, by_id, target, theme)

    if curated:
        clips = [ScenarioClip(media_id=mid, duration=per_photo, text=title)
                 for mid, title in curated["clips"]]
        return Scenario(title=theme or "Montage", engine="tchavi",
                        rationale=curated["rationale"], clips=clips, rejected=rejected)

    # Repli déterministe : les mieux notées, remises en ordre chronologique.
    best = sorted(candidates, key=lambda m: by_id[m.id].score, reverse=True)[:target]
    keep_ids = {m.id for m in best}
    ordered = [m for m in candidates if m.id in keep_ids]
    return Scenario(
        title=theme or "Montage", engine="rule_based",
        rationale=(f"{len(ordered)} photos retenues sur {len(photos)} d'après la "
                   "netteté, l'exposition et la présence de personnes ; ordre "
                   "chronologique."),
        clips=[ScenarioClip(media_id=m.id, duration=per_photo) for m in ordered],
        rejected=rejected,
    )
