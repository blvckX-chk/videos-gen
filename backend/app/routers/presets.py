"""Presets / pipelines de départ — points d'entrée guidés (anti page-vide).

Source unique côté serveur : le panel et (plus tard) les pipelines s'appuient
dessus. Données statiques, pas de modèle — simple et extensible.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api")


class Preset(BaseModel):
    id: str
    label: str
    icon: str          # emoji simple, remplacé par une vraie icône plus tard
    description: str
    mode: str          # video | poster | campaign | copy
    prompt: str        # texte pré-rempli dans la console KORA
    accent: str        # teinte de la vignette (dégradé CSS côté front)


_PRESETS: list[Preset] = [
    Preset(id="explainer", label="Explainer", icon="🎓", mode="video", accent="g2",
           description="Vidéo pédagogique claire à partir d'un document.",
           prompt="Transforme ce document en vidéo explicative claire et rythmée, format 9:16, ton pédagogique."),
    Preset(id="promo", label="Promo produit", icon="🏷️", mode="video", accent="g1",
           description="Pub courte percutante pour une offre ou un produit.",
           prompt="Crée une pub verticale 15s pour promouvoir mon produit, accroche forte, call-to-action clair."),
    Preset(id="trailer", label="Teaser ciné", icon="🎬", mode="video", accent="g3",
           description="Teaser cinématique court et impactant.",
           prompt="Monte un teaser cinématique 16:9 de 10s, ambiance intense, titre final percutant."),
    Preset(id="motion_comic", label="Motion comic", icon="💥", mode="video", accent="g3",
           description="Anime une BD / un manga case par case.",
           prompt="Anime ma BD en motion comic : enchaîne les cases avec zoom et transitions, voix des personnages."),
    Preset(id="poster", label="Affiche", icon="🖼️", mode="poster", accent="g4",
           description="Affiche ou visuel réseaux prêt à publier.",
           prompt="Conçois une affiche carrée pour une promo -20%, charte blvckUnlimited, texte lisible."),
    Preset(id="social_short", label="Short réseaux", icon="📱", mode="video", accent="g5",
           description="Format vertical rythmé pour TikTok / Reels.",
           prompt="Fais un short vertical 9:16 dynamique pour les réseaux, sous-titres intégrés."),
    Preset(id="campaign", label="Campagne 360°", icon="🚀", mode="campaign", accent="g1",
           description="Un brief → vidéo + affiche + copy d'un coup.",
           prompt="Prépare une campagne 360° complète pour promouvoir mon activité : vidéo, affiche et textes."),
    Preset(id="copy", label="Copywriting", icon="✍️", mode="copy", accent="g2",
           description="Accroches, légendes et hashtags par plateforme.",
           prompt="Écris le copy multi-plateformes (TikTok, Instagram, LinkedIn) pour promouvoir mon offre."),
]


@router.get("/presets", response_model=list[Preset])
async def list_presets() -> list[Preset]:
    return _PRESETS
