"""Résolution du rôle et des droits (entitlements) + décision de filigrane.

Deux modes, selon que `ADMIN_SECRET` est configuré :

- **Dev/solo** (secret vide) : rôle ADMIN par défaut, l'en-tête `X-Role`
  permet de simuler free/premium. L'opérateur a un accès total sans rien
  configurer (« moi d'abord »).
- **Production** (secret défini) : ADMIN uniquement si la requête présente
  le bon secret (`X-Admin-Secret`). Sinon le rôle par défaut est FREE et
  `X-Role` ne peut sélectionner que free/premium (pas d'auto-promotion admin).

Le filigrane et les tiers étant décidés côté serveur à partir du rôle ainsi
résolu, cette porte est le seul point à sécuriser pour rendre les garde-fous
(filigrane forcé, quotas free) non contournables par un simple en-tête.
"""
from __future__ import annotations

import hmac

from ..config import get_settings
from .schema import Entitlements, Role

# Table des droits par rôle. Les quotas sont posés mais non encore comptés.
_TABLE: dict[Role, Entitlements] = {
    Role.ADMIN: Entitlements(
        role=Role.ADMIN,
        watermark_forced=False, watermark_removable=True,
        allowed_tier="premium", daily_quota=None, max_resolution=None,
        batch_allowed=True,
    ),
    Role.PREMIUM: Entitlements(
        role=Role.PREMIUM,
        watermark_forced=False, watermark_removable=True,
        allowed_tier="premium", daily_quota=None, max_resolution=None,
        batch_allowed=True,
    ),
    Role.FREE: Entitlements(
        role=Role.FREE,
        watermark_forced=True, watermark_removable=False,
        allowed_tier="free", daily_quota=10, max_resolution=1920,
        batch_allowed=False,
    ),
}


def get_entitlements(role: Role) -> Entitlements:
    return _TABLE[role]


def admin_secret_ok(provided: str | None) -> bool:
    """Vrai si un secret admin est configuré ET que `provided` le vaut
    (comparaison à temps constant). Faux si aucun secret n'est configuré."""
    expected = get_settings().admin_secret
    if not expected:
        return False
    return bool(provided) and hmac.compare_digest(provided.strip(), expected)


def resolve_role(x_role: str | None = None, admin_secret: str | None = None) -> Role:
    """Rôle courant, selon le mode d'authentification.

    Production (secret configuré) :
      - bon `admin_secret` → ADMIN ;
      - sinon, `X-Role` limité à {free, premium} ; défaut = FREE.
    Dev/solo (aucun secret configuré) :
      - `X-Role` peut tout simuler ; défaut = ADMIN.
    """
    secret_configured = bool(get_settings().admin_secret)

    if secret_configured:
        if admin_secret_ok(admin_secret):
            return Role.ADMIN
        if x_role:
            try:
                role = Role(x_role.strip().lower())
                if role != Role.ADMIN:  # pas d'auto-promotion admin via en-tête
                    return role
            except ValueError:
                pass
        return Role.FREE

    # Dev/solo : frictionless
    if x_role:
        try:
            return Role(x_role.strip().lower())
        except ValueError:
            pass
    return Role.ADMIN


def resolve_entitlements(
    x_role: str | None = None, admin_secret: str | None = None
) -> Entitlements:
    return get_entitlements(resolve_role(x_role, admin_secret))


def effective_tier(ent: Entitlements, requested_tier: str) -> str:
    """Contraint le tier demandé par le rôle : un free ne peut pas monter en premium."""
    if ent.allowed_tier == "free" and requested_tier == "premium":
        return "free"
    return requested_tier


def effective_watermark(
    ent: Entitlements,
    requested: str | None,
    default_text: str = "blvckUnlimited",
) -> str | None:
    """Filigrane effectif pour un livrable image, décidé côté serveur.

    - Rôle à filigrane forcé (free) : toujours `default_text`, quoi que
      demande le client (garde-fou non contournable).
    - Rôle autorisé (admin/premium) : honore la demande — `None` = pas de
      filigrane, sinon le texte fourni (logo/nom du client).
    """
    if ent.watermark_forced or not ent.watermark_removable:
        return default_text
    return requested


def decide_watermark(
    ent: Entitlements,
    requested_remove: bool = False,
    custom_text: str | None = None,
    default_text: str = "blvckUnlimited",
) -> tuple[bool, str]:
    """Renvoie (appliquer_le_filigrane, texte).

    - Rôle à filigrane forcé (free) : toujours appliqué, texte blvckUnlimited,
      non retirable et non personnalisable.
    - Rôle autorisé (admin/premium) : peut retirer (requested_remove) ou
      personnaliser le texte (custom_text, ex. logo/nom du client).
    """
    if ent.watermark_forced or not ent.watermark_removable:
        return True, default_text
    if requested_remove:
        return False, ""
    return True, (custom_text or default_text)
