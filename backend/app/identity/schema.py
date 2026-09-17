"""Schémas identité : rôles, droits (entitlements) et chartes de marque.

Deux axes distincts (voir cahier des charges §13) :
  - le RÔLE d'un utilisateur (admin / premium / free) → ses droits & limites ;
  - le TIER d'un job (free / premium) → quels providers il peut appeler.
Le rôle **contraint** le tier.

Principe « moi d'abord » : le rôle par défaut est ADMIN — l'opérateur a un
accès total, sans filigrane forcé ni limite, tant qu'aucune authentification
n'est branchée (Slice 7 — persistance & comptes).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Role(str, Enum):
    ADMIN = "admin"       # toi — accès total
    PREMIUM = "premium"   # client payant
    FREE = "free"         # gratuit, filigrane forcé, limites


class Entitlements(BaseModel):
    """Droits dérivés d'un rôle, vérifiés à chaque job."""
    role: Role
    #: le filigrane blvckUnlimited est-il imposé et non retirable ?
    watermark_forced: bool
    #: l'utilisateur peut-il retirer / personnaliser le filigrane ?
    watermark_removable: bool
    #: tier de coût maximal autorisé
    allowed_tier: str            # "free" | "premium"
    #: quota de générations/jour (None = illimité) — posé, non encore compté
    daily_quota: Optional[int]
    #: résolution max (None = illimitée)
    max_resolution: Optional[int]
    #: droit aux campagnes en lot
    batch_allowed: bool


class Charte(BaseModel):
    """Charte de marque d'un client ou d'un pôle."""
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    #: palette de tokens (bg1, bg2, fg, muted, accent, accent2…)
    palette: dict[str, str]
    logo_url: Optional[str] = None
    font: Optional[str] = None
    tone: Optional[str] = None
    #: texte de filigrane propre au client (si autorisé par le rôle)
    watermark_text: Optional[str] = None
    #: rattachement optionnel à un pôle interne
    pole: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CharteProposalRequest(BaseModel):
    """Entrées de clarification pour proposer une charte quand le client n'en a pas."""
    sector: Optional[str] = None       # secteur d'activité
    ambiance: Optional[str] = None     # moderne | chaleureux | luxe | dynamique | nature | sobre
    references: Optional[str] = None   # 2-3 marques de référence (texte libre)
    audience: Optional[str] = None     # public cible
    name_hint: Optional[str] = None    # nom du client / de la marque
