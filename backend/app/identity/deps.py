"""Dépendances FastAPI pour l'authentification et les droits.

Centralise la lecture des en-têtes `X-Role` / `X-Admin-Secret` pour que
chaque route obtienne des `Entitlements` déjà résolus (et donc un filigrane
et un tier décidés côté serveur, non contournables par un simple en-tête).
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from .entitlements import resolve_entitlements
from .schema import Entitlements, Role


def current_entitlements(
    x_role: str | None = Header(default=None),
    x_admin_secret: str | None = Header(default=None),
) -> Entitlements:
    return resolve_entitlements(x_role, x_admin_secret)


def require_admin(
    ent: Entitlements = Depends(current_entitlements),
) -> Entitlements:
    """Garde pour les routes réservées à l'admin (secret requis en prod)."""
    if ent.role != Role.ADMIN:
        raise HTTPException(403, "Réservé à l'administrateur (secret admin requis).")
    return ent
