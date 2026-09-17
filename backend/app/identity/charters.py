"""Chartes de marque : stockage, génération de palette harmonieuse, proposition.

Quand un client n'a pas de charte, le système en **propose** après quelques
questions. La génération de palette est **déterministe** (théorie des couleurs
via colorsys) — gratuite, sans LLM — et peut être enrichie par un LLM pour le
nom et le ton (facultatif).
"""
from __future__ import annotations

import colorsys

from .schema import Charte, CharteProposalRequest

# --------------------------------------------------------------------------- #
# Store en mémoire (persistance → Slice 7)
# --------------------------------------------------------------------------- #
_CHARTES: dict[str, Charte] = {}


def save_charte(c: Charte) -> Charte:
    _CHARTES[c.id] = c
    return c


def get_charte(cid: str) -> Charte | None:
    return _CHARTES.get(cid)


def list_chartes() -> list[Charte]:
    return sorted(_CHARTES.values(), key=lambda c: c.created_at, reverse=True)


def delete_charte(cid: str) -> bool:
    return _CHARTES.pop(cid, None) is not None


# --------------------------------------------------------------------------- #
# Couleurs
# --------------------------------------------------------------------------- #
def _hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0, min(1, l)), max(0, min(1, s)))
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def palette_from_hue(hue_deg: float) -> dict[str, str]:
    """Palette sombre cohérente autour d'une teinte d'accent (degrés 0-360).
    Fond légèrement teinté vers l'accent → identité, pas gris neutre."""
    h = (hue_deg % 360) / 360.0
    comp = (h + 150 / 360.0)  # accent secondaire analogue-complémentaire
    return {
        "bg1": _hex(h, 0.18, 0.07),
        "bg2": _hex(h, 0.16, 0.12),
        "fg": _hex(h, 0.10, 0.94),
        "muted": _hex(h, 0.12, 0.66),
        "accent": _hex(h, 0.70, 0.58),
        "accent2": _hex(comp, 0.55, 0.60),
        "accent_soft": _hex(h, 0.35, 0.16),
        "positive": "#6FC077",
        "negative": "#E06B4F",
    }


# Ambiance → teinte(s) d'accent candidates (degrés)
_AMBIANCE_HUES: dict[str, list[float]] = {
    "luxe": [42, 280],          # or, pourpre
    "moderne": [205, 190],      # bleu, cyan
    "tech": [205, 260],
    "chaleureux": [24, 8],      # orange, terracotta
    "nature": [140, 100],       # vert
    "dynamique": [350, 20],     # rouge/magenta, orange
    "sobre": [220, 210],        # bleu-gris
}

_HUE_NAMES = {
    42: "Or chaud", 280: "Pourpre profond", 205: "Bleu nuit", 190: "Cyan moderne",
    260: "Indigo", 24: "Ambre", 8: "Terracotta", 140: "Vert forêt", 100: "Vert olive",
    350: "Rouge magenta", 20: "Orange vif", 220: "Bleu ardoise", 210: "Bleu acier",
}


def propose_chartes(req: CharteProposalRequest, count: int = 3) -> list[Charte]:
    """Propose `count` pistes de charte à partir des réponses de clarification.
    Déterministe et gratuit."""
    ambiance = (req.ambiance or "moderne").strip().lower()
    hues = _AMBIANCE_HUES.get(ambiance, _AMBIANCE_HUES["moderne"])
    # compléter si peu de teintes pour l'ambiance
    while len(hues) < count:
        hues = hues + [(hues[-1] + 40) % 360]

    brand = (req.name_hint or req.sector or "Marque").strip()
    tone = _tone_for(ambiance)
    out: list[Charte] = []
    for i in range(count):
        hue = hues[i % len(hues)]
        pal = palette_from_hue(hue)
        color_name = _HUE_NAMES.get(hue, "Signature")
        out.append(Charte(
            name=f"{brand} — {color_name}",
            palette=pal,
            tone=tone,
            watermark_text=brand if req.name_hint else None,
            font="Inter / Bricolage Grotesque",
        ))
    return out


def _tone_for(ambiance: str) -> str:
    return {
        "luxe": "élégant, épuré, premium",
        "moderne": "dynamique, clair, contemporain",
        "tech": "précis, innovant, confiant",
        "chaleureux": "accueillant, humain, proche",
        "nature": "authentique, apaisant, durable",
        "dynamique": "énergique, direct, percutant",
        "sobre": "professionnel, sobre, rassurant",
    }.get(ambiance, "clair et professionnel")
