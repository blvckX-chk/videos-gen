"""Opérations FFmpeg du montage — qualité de sortie « pro ».

Principes tenus ici :

1. **Normalisation avant assemblage.** Chaque plan sort avec exactement les
   mêmes paramètres vidéo ET audio. Sans cela, assembler un rush de téléphone,
   un clip stock et une photo casse le montage.
2. **Le son des rushes est conservé.** Un plan sans audio reçoit une piste de
   silence, afin que tous les plans restent concaténables.
3. **Le cadre est rempli** (recadrage) plutôt que complété par des bandes
   noires : le letterbox est le premier signe d'un montage amateur.
4. **Le mixage final est normalisé en loudness** (EBU R128, ‑14 LUFS, cible des
   plateformes sociales), avec atténuation de la musique sous la voix.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger("videos_gen.montage")

#: Encodage vidéo identique pour tous les plans → concaténation sans ré-encodage.
_VENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p"]
#: Encodage audio identique pour tous les plans (indispensable au concat).
_AENC = ["-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k"]
_MUX = ["-movflags", "+faststart"]

#: Durée d'un fondu enchaîné entre deux plans.
DISSOLVE = 0.45

_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)


async def _run(*cmd: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        tail = (err or b"").decode(errors="replace")[-600:]
        raise RuntimeError(f"ffmpeg: {tail}")


async def has_audio(path: Path) -> bool:
    """Le fichier porte-t-il une piste audio exploitable ?"""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "json", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    out, _ = await proc.communicate()
    try:
        return bool(json.loads(out or b"{}").get("streams"))
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------- Filtres --- #
def _frame_filter(w: int, h: int, fit: str) -> str:
    """Mise au format. `cover` remplit le cadre en recadrant (défaut, rendu pro) ;
    `contain` conserve tout en ajoutant des bandes."""
    if fit == "contain":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}")


def _ken_burns_filter(w: int, h: int, fps: int, duration: float, fit: str) -> str:
    """Zoom lent sur une image fixe : évite l'effet diaporama."""
    frames = max(1, int(round(duration * fps)))
    big_w, big_h = w * 2, h * 2
    base = _frame_filter(big_w, big_h, fit)
    return (f"{base},zoompan=z='min(zoom+0.0012,1.12)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={w}x{h}:fps={fps}")


def _font_file() -> str | None:
    for f in _FONTS:
        if Path(f).exists():
            return f
    return None


def _esc_drawtext(text: str) -> str:
    """Échappe le texte pour drawtext (\\ : ' %)."""
    return (text.replace("\\", "\\\\").replace(":", "\\:")
                .replace("'", "\\'").replace("%", "\\%"))


def _title_filter(text: str, w: int, h: int) -> str:
    """Titre incrusté, bas-centré, lisible sur n'importe quelle image."""
    size = max(22, int(h / 22))
    font = _font_file()
    f = f"fontfile={font}:" if font else ""
    return (f"drawtext={f}text='{_esc_drawtext(text)}':"
            f"fontcolor=white:fontsize={size}:"
            f"borderw={max(2, size // 14)}:bordercolor=black@0.85:"
            f"box=1:boxcolor=black@0.35:boxborderw={max(8, size // 2)}:"
            f"x=(w-tw)/2:y=h-th-{int(h * 0.12)}")


def _silence_input() -> list[str]:
    return ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]


# ---------------------------------------------------------- Normalisation --- #
async def normalize_photo(src: Path, out: Path, *, w: int, h: int, fps: int,
                          duration: float, ken_burns: bool = False,
                          fade_in: bool = False, fit: str = "cover",
                          text: str | None = None) -> Path:
    """Photo → plan vidéo de `duration` secondes (avec piste de silence).

    La durée est bornée en nombre d'images (`-frames:v`) et non par `-t` : avec
    `zoompan`, qui émet d images pour CHAQUE image reçue, une entrée en boucle
    multiplierait la durée (bug observé : 2 s rendues en 100 s)."""
    frames = max(1, int(round(duration * fps)))
    vf = (_ken_burns_filter(w, h, fps, duration, fit) if ken_burns
          else f"{_frame_filter(w, h, fit)},fps={fps}")
    vf += ",setsar=1,format=yuv420p"
    if text:
        vf += "," + _title_filter(text, w, h)
    if fade_in:
        vf += ",fade=t=in:st=0:d=0.4"

    cmd = ["ffmpeg", "-y"]
    if not ken_burns:
        cmd += ["-loop", "1"]
    cmd += ["-i", str(src), *_silence_input(),
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf, "-frames:v", str(frames), "-r", str(fps),
            *_VENC, *_AENC, "-shortest", *_MUX, str(out)]
    await _run(*cmd)
    return out


async def normalize_video(src: Path, out: Path, *, w: int, h: int, fps: int,
                          duration: float, in_point: float = 0.0,
                          fade_in: bool = False, fit: str = "cover",
                          text: str | None = None) -> Path:
    """Extrait d'une vidéo normalisé au format cible, **son conservé**."""
    vf = f"{_frame_filter(w, h, fit)},fps={fps},setsar=1,format=yuv420p"
    if text:
        vf += "," + _title_filter(text, w, h)
    if fade_in:
        vf += ",fade=t=in:st=0:d=0.4"

    src_has_audio = await has_audio(src)
    cmd = ["ffmpeg", "-y"]
    if in_point > 0:
        cmd += ["-ss", f"{in_point:.3f}"]          # seek avant -i : rapide
    cmd += ["-i", str(src)]
    if not src_has_audio:
        cmd += _silence_input()                     # garder tous les plans concaténables
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0"]
    cmd += ["-t", f"{duration:.3f}", "-vf", vf, "-r", str(fps),
            *_VENC, *_AENC, "-shortest", *_MUX, str(out)]
    await _run(*cmd)
    return out


# -------------------------------------------------------------- Assemblage --- #
async def concat_cut(parts: list[Path], out: Path) -> Path:
    """Coupes franches : démuxeur concat, sans ré-encodage (rapide)."""
    if not parts:
        raise ValueError("Aucun plan à assembler.")
    listing = out.parent / f"{out.stem}.concat.txt"
    quote = chr(39)
    listing.write_text(
        "".join(f"file {quote}{str(p).replace(quote, quote + chr(92) + quote + quote)}{quote}\n"
                for p in parts),
        encoding="utf-8",
    )
    try:
        await _run("ffmpeg", "-y", "-f", "concat", "-safe", "0",
                   "-i", str(listing), "-c", "copy", *_MUX, str(out))
    finally:
        listing.unlink(missing_ok=True)
    return out


#: Au-delà, on fond par groupes plutôt qu'en une seule commande : un album de
#: plusieurs dizaines de photos saturerait un unique graphe de filtres.
_MAX_XFADE_INPUTS = 12


async def concat_dissolve(parts: list[Path], durations: list[float], out: Path,
                          *, fps: int, d: float = DISSOLVE) -> Path:
    """Fondus enchaînés entre plans, par groupes si le montage est long."""
    if len(parts) == 1:
        return await concat_cut(parts, out)
    if len(parts) <= _MAX_XFADE_INPUTS:
        await _dissolve_chain(parts, durations, out, fps=fps, d=d)
        return out

    groups: list[Path] = []
    group_durations: list[float] = []
    for gi in range(0, len(parts), _MAX_XFADE_INPUTS):
        chunk = parts[gi:gi + _MAX_XFADE_INPUTS]
        chunk_dur = durations[gi:gi + _MAX_XFADE_INPUTS]
        if len(chunk) == 1:
            groups.append(chunk[0])
            group_durations.append(chunk_dur[0])
            continue
        gout = out.parent / f"{out.stem}.g{gi // _MAX_XFADE_INPUTS:03d}.mp4"
        total = await _dissolve_chain(chunk, chunk_dur, gout, fps=fps, d=d)
        groups.append(gout)
        group_durations.append(total)

    # Les groupes sont eux-mêmes enchaînés en fondu (récursif si besoin).
    return await concat_dissolve(groups, group_durations, out, fps=fps, d=d)


async def _dissolve_chain(parts: list[Path], durations: list[float], out: Path,
                          *, fps: int, d: float) -> float:
    """Une passe de fondus enchaînés (xfade vidéo + acrossfade audio).

    Les plans se chevauchent : la durée totale diminue d'autant, ce qui est le
    comportement attendu d'un fondu enchaîné. Renvoie la durée obtenue."""
    cmd: list[str] = ["ffmpeg", "-y"]
    for p in parts:
        cmd += ["-i", str(p)]

    fc: list[str] = []
    v_cur, a_cur = "[0:v]", "[0:a]"
    acc = durations[0]
    for i in range(1, len(parts)):
        # le fondu ne peut dépasser la moitié du plus court des deux plans
        di = max(0.1, min(d, durations[i] / 2, durations[i - 1] / 2))
        offset = max(0.0, acc - di)
        fc.append(f"{v_cur}[{i}:v]xfade=transition=fade:duration={di:.3f}:"
                  f"offset={offset:.3f}[v{i}]")
        fc.append(f"{a_cur}[{i}:a]acrossfade=d={di:.3f}:c1=tri:c2=tri[a{i}]")
        v_cur, a_cur = f"[v{i}]", f"[a{i}]"
        acc = acc + durations[i] - di

    cmd += ["-filter_complex", ";".join(fc),
            "-map", v_cur, "-map", a_cur,
            "-r", str(fps), *_VENC, *_AENC, *_MUX, str(out)]
    await _run(*cmd)
    return acc


# ------------------------------------------------------------------ Audio --- #
async def mix_tracks(video_in: Path, out: Path, *, voice: Path | None = None,
                     music: Path | None = None, music_volume: float = 0.35) -> Path:
    """Mixe son d'origine + voix off + musique, puis normalise le loudness.

    La musique est atténuée sous la voix par compression sidechain (ducking),
    comme le ferait un monteur. Sortie calée sur ‑14 LUFS (cible sociale)."""
    cmd: list[str] = ["ffmpeg", "-y", "-i", str(video_in)]
    idx = 1
    voice_i = music_i = None
    if voice is not None:
        cmd += ["-i", str(voice)]; voice_i = idx; idx += 1
    if music is not None:
        # la musique boucle si elle est plus courte que la vidéo
        cmd += ["-stream_loop", "-1", "-i", str(music)]; music_i = idx; idx += 1

    fc: list[str] = ["[0:a]volume=1.0[src]"]
    sources = ["[src]"]

    if voice_i is not None:
        fc.append(f"[{voice_i}:a]volume=1.0[vo]")
    if music_i is not None:
        fc.append(f"[{music_i}:a]volume={music_volume}[mus]")
        if voice_i is not None:
            # ducking : la voix pilote l'atténuation de la musique
            fc.append("[mus][vo]sidechaincompress=threshold=0.03:ratio=10:"
                      "attack=15:release=400[musd]")
            sources += ["[vo]", "[musd]"]
        else:
            sources.append("[mus]")
    elif voice_i is not None:
        sources.append("[vo]")

    if len(sources) > 1:
        fc.append(f"{''.join(sources)}amix=inputs={len(sources)}:"
                  f"duration=first:dropout_transition=0,"
                  f"loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    else:
        fc.append("[src]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    cmd += ["-filter_complex", ";".join(fc),
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", *_AENC, "-shortest", *_MUX, str(out)]
    await _run(*cmd)
    return out


# -------------------------------------------------------------- Filigrane --- #
async def burn_watermark(src: Path, out: Path, text: str, *, height: int) -> Path:
    """Incruste le filigrane dans l'image (non retirable après coup).

    Décidé côté serveur selon le rôle : un utilisateur gratuit ne peut pas
    l'enlever, puisqu'il est gravé dans les pixels au rendu."""
    size = max(14, int(height / 40))
    font = _font_file()
    f = f"fontfile={font}:" if font else ""
    draw = (f"drawtext={f}text='{_esc_drawtext(text)}':"
            f"fontcolor=white@0.72:fontsize={size}:"
            f"box=1:boxcolor=black@0.22:boxborderw={max(5, size // 3)}:"
            f"x=w-tw-{size}:y=h-th-{size}")
    await _run("ffmpeg", "-y", "-i", str(src), "-vf", draw,
               *_VENC, "-c:a", "copy", *_MUX, str(out))
    return out
