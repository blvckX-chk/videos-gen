"""Résolution du rôle et des droits (entitlements) + décision de filigrane.

Le rôle vient de l'en-tête `X-Role` (pour tester free/premium) et, par défaut,
vaut ADMIN — l'opérateur a un accès total sans rien configurer (« moi d'abord »).
Quand l'authentification arrivera (Slice 7), `resolve_role` lira le compte
authentifié au lieu de l'en-tête.
"""
from __future__ import annotations

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


def resolve_role(x_role: str | None = None) -> Role:
    """Rôle courant. Défaut = ADMIN (accès total). `X-Role` permet de simuler
    free/premium pour tester l'application des droits."""
    if x_role:
        try:
            return Role(x_role.strip().lower())
        except ValueError:
            pass
    return Role.ADMIN


def resolve_entitlements(x_role: str | None = None) -> Entitlements:
    return get_entitlements(resolve_role(x_role))


def effective_tier(ent: Entitlements, requested_tier: str) -> str:
    """Contraint le tier demandé par le rôle : un free ne peut pas monter en premium."""
    if ent.allowed_tier == "free" and requested_tier == "premium":
        return "free"
    return requested_tier


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
