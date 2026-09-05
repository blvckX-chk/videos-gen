"""Post-production ffmpeg : MP4 muet + voix + musique + sous-titres → MP4 final.

Une seule passe ffmpeg via filter_complex :
  - mixe la voix (plein volume) et la musique (atténuée / ducking simple) ;
  - incruste les sous-titres SRT (burn-in) avec un style lisible en bas ;
  - copie la vidéo si aucun sous-titre, sinon ré-encode (obligatoire pour burn).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

_SUB_STYLE = (
    "FontName=DejaVu Sans,FontSize=15,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&HA0000000,BorderStyle=1,"
    "Outline=2,Shadow=1,Alignment=2,MarginV=90"
)


async def _run(*cmd: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg postprod: {err[-400:].decode(errors='replace')}")


def _esc_sub_path(p: Path) -> str:
    # Dans un filtre ffmpeg, échapper : \ ' [ ] , et :
    s = str(p)
    for ch in ("\\", ":", "'", "[", "]", ","):
        s = s.replace(ch, "\\" + ch)
    return s


async def postprocess(
    video_in: Path, out: Path,
    voice: Path | None = None, music: Path | None = None,
    srt: Path | None = None, music_volume: float = 0.16,
) -> Path:
    cmd: list[str] = ["ffmpeg", "-y", "-i", str(video_in)]
    idx = 1
    voice_idx = music_idx = None
    if voice is not None:
        cmd += ["-i", str(voice)]; voice_idx = idx; idx += 1
    if music is not None:
        cmd += ["-i", str(music)]; music_idx = idx; idx += 1

    fc: list[str] = []

    # --- Vidéo (avec ou sans burn-in des sous-titres) ---
    if srt is not None:
        fc.append(f"[0:v]subtitles=filename='{_esc_sub_path(srt)}':force_style='{_SUB_STYLE}'[vout]")
        vmap = "[vout]"
        vcodec = ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
    else:
        vmap = "0:v"
        vcodec = ["-c:v", "copy"]

    # --- Audio ---
    amap: str | None = None
    if voice_idx is not None and music_idx is not None:
        fc.append(f"[{voice_idx}:a]volume=1.0[vv]")
        fc.append(f"[{music_idx}:a]volume={music_volume}[mm]")
        fc.append("[vv][mm]amix=inputs=2:duration=first:dropout_transition=0[aout]")
        amap = "[aout]"
    elif voice_idx is not None:
        amap = f"{voice_idx}:a"
    elif music_idx is not None:
        fc.append(f"[{music_idx}:a]volume={music_volume}[aout]")
        amap = "[aout]"

    if fc:
        cmd += ["-filter_complex", ";".join(fc)]
    cmd += ["-map", vmap]
    if amap is not None:
        cmd += ["-map", amap, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += vcodec + [str(out)]

    await _run(*cmd)
    if not out.exists():
        raise RuntimeError("postprod : fichier de sortie manquant.")
    return out
