"""Extraction de points clés depuis le texte d'un document (sans LLM).

Heuristiques simples et robustes : titres = lignes courtes, points clés =
phrases de longueur moyenne. Suffisant pour un storyboard règle-based gratuit.
"""
from __future__ import annotations

import re

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_WS = re.compile(r"\s+")


def clean_lines(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.strip()]


def normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def first_heading(text: str, max_len: int = 90) -> str | None:
    """Première ligne courte = titre probable de la page/section."""
    for line in clean_lines(text):
        if 3 <= len(line) <= max_len and not line.endswith((".", ",", ";")):
            return normalize(line)
    return None


def sentences(text: str) -> list[str]:
    return [normalize(s) for s in _SENT_SPLIT.split(text) if normalize(s)]


def key_points(text: str, limit: int = 3, min_words: int = 4, max_words: int = 26) -> list[str]:
    """Sélectionne les phrases « affichables » : ni trop courtes ni trop longues."""
    out: list[str] = []
    seen: set[str] = set()
    for s in sentences(text):
        wc = len(s.split())
        if min_words <= wc <= max_words:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                out.append(s)
        if len(out) >= limit:
            break
    return out


def shorten(text: str, max_chars: int = 90) -> str:
    text = normalize(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"
