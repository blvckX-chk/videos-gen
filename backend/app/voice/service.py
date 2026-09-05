"""Synthèse de la voix off d'un storyboard + génération des sous-titres.

Produit :
  - une **piste voix** unique alignée sur la timeline vidéo (un segment par
    shot, de durée exactement égale à celle du shot — la voix trop longue est
    accélérée jusqu'à 1.6× puis rognée, la voix trop courte est complétée par
    du silence) ;
  - un **SRT** déterministe (voir captions.py) ;
  - le **coût** estimé (0 pour les providers gratuits).
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

from ..models import Tier
from ..storyboard.schema import Storyboard
from . import captions as cap
from .providers.base import TTSProvider
from .providers.registry import default_free_tts, get_tts_provider


def _probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return float(r.stdout.strip())
    except (ValueError, TypeError):
        return 0.0


async def _run(*cmd: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg: {err[-300:].decode(errors='replace')}")


async def _silence(dur: float, out: Path) -> None:
    await _run("ffmpeg", "-y", "-f", "lavfi",
               "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{dur:.3f}",
               "-q:a", "9", str(out))


async def _fit_segment(voice_wav: Path, shot_dur: float, out: Path) -> None:
    """Ajuste la voix à la durée exacte du shot (atempo ≤ 1.6× puis pad/trim)."""
    vdur = _probe_duration(voice_wav)
    if vdur <= 0:
        await _silence(shot_dur, out)
        return
    ratio = vdur / shot_dur
    af = "apad"
    if ratio > 1.02:
        tempo = min(1.6, ratio)
        af = f"atempo={tempo:.3f},apad"
    await _run("ffmpeg", "-y", "-i", str(voice_wav), "-af", af,
               "-t", f"{shot_dur:.3f}", "-ar", "44100", "-ac", "2",
               "-q:a", "5", str(out))


def _pick_provider(provider_id: str | None, tier: Tier) -> TTSProvider:
    prov = get_tts_provider(provider_id) if provider_id else default_free_tts()
    if prov is None:
        raise RuntimeError(f"Provider TTS inconnu : {provider_id}")
    if not prov.is_available():
        raise RuntimeError(f"Provider TTS '{prov.id}' indisponible.")
    if tier == Tier.FREE and not prov.free:
        raise PermissionError(f"Provider TTS '{prov.id}' payant → interdit sur tier free.")
    return prov


async def synthesize_storyboard(
    sb: Storyboard, out_dir: Path,
    provider_id: str | None = None, tier: Tier = Tier.FREE,
    voice: str | None = None,
) -> tuple[Path | None, Path | None, int]:
    """Renvoie (voice_track_path, srt_path, cost_cents). Les deux chemins sont
    None si le storyboard ne contient aucune narration."""
    shots = [sh for sc in sb.scenes for sh in sc.shots]
    if not any((sh.narration or sh.text) for sh in shots):
        return None, None, 0

    prov = _pick_provider(provider_id, tier)
    out_dir.mkdir(parents=True, exist_ok=True)
    lang = sb.language or "fr"
    cost = 0

    seg_paths: list[Path] = []
    cues: list[cap.Cue] = []
    cursor = 0.0

    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        for i, sh in enumerate(shots):
            shot_dur = float(sh.duration)
            narration = (sh.narration or sh.text or "").strip()
            seg = tmpd / f"seg_{i:03d}.m4a"
            if narration:
                raw = tmpd / f"raw_{i:03d}.wav"
                await prov.synthesize(narration, raw, voice=voice, lang=lang)
                await _fit_segment(raw, shot_dur, seg)
                if hasattr(prov, "estimated_cost_cents"):
                    cost += prov.estimated_cost_cents(narration)  # type: ignore[attr-defined]
                cues.extend(cap.shot_cues(cursor, cursor + shot_dur, narration))
            else:
                await _silence(shot_dur, seg)
            seg_paths.append(seg)
            cursor += shot_dur

        # Concat de tous les segments → piste voix unique
        concat_list = tmpd / "list.txt"
        concat_list.write_text("".join(f"file '{p}'\n" for p in seg_paths), encoding="utf-8")
        voice_track = out_dir / f"voice_{sb.id}.m4a"
        await _run("ffmpeg", "-y", "-f", "concat", "-safe", "0",
                   "-i", str(concat_list), "-c", "copy", str(voice_track))

    srt_path = out_dir / f"cap_{sb.id}.srt"
    srt_path.write_text(cap.to_srt(cues), encoding="utf-8")
    return voice_track, srt_path, cost
