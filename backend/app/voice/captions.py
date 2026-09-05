"""Génération de sous-titres SANS ASR.

Comme on génère nous-mêmes la narration, on connaît le texte et la fenêtre
temporelle de chaque shot. On répartit les mots en lignes courtes, réparties
proportionnellement dans l'intervalle du shot → SRT propre, gratuit, offline.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cue:
    start: float   # secondes
    end: float
    text: str


def _fmt(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunk_words(text: str, max_words: int = 7) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)] or [""]


def shot_cues(start: float, end: float, narration: str,
              max_words: int = 7) -> list[Cue]:
    """Découpe la narration d'un shot en cues répartis sur [start, end]
    proportionnellement au nombre de mots de chaque ligne."""
    narration = (narration or "").strip()
    if not narration:
        return []
    lines = _chunk_words(narration, max_words)
    total_words = sum(len(l.split()) for l in lines) or 1
    span = max(0.4, end - start)
    cues: list[Cue] = []
    cursor = start
    for line in lines:
        w = len(line.split()) or 1
        dur = span * (w / total_words)
        cues.append(Cue(start=cursor, end=min(end, cursor + dur), text=line))
        cursor += dur
    return cues


def to_srt(cues: list[Cue]) -> str:
    out: list[str] = []
    for i, c in enumerate(cues, 1):
        out.append(str(i))
        out.append(f"{_fmt(c.start)} --> {_fmt(c.end)}")
        out.append(c.text)
        out.append("")
    return "\n".join(out)
