"""Opérations FFmpeg du montage : normaliser, découper, concaténer.

Point clé de fiabilité : on **normalise chaque plan** (même résolution, même
fps, même SAR, mêmes paramètres d'encodage) AVANT de concaténer. Sans cette
étape, la concaténation de clips hétérogènes (un rush de téléphone + un clip
stock + une photo) produit une vidéo cassée ou refuse de s'assembler.

Les plans sont rendus sans audio : la piste son (voix off, musique) est
ajoutée en une passe par la post-production existante.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger("videos_gen.montage")

#: Paramètres d'encodage identiques pour tous les plans → concat sans ré-encodage.
_ENC = [
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
]


async def _run(*cmd: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        tail = (err or b"").decode(errors="replace")[-500:]
        raise RuntimeError(f"ffmpeg: {tail}")


def _fit_filter(w: int, h: int) -> str:
    """Met à l'échelle sans déformer, puis complète par des bandes centrées."""
    return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")


def _ken_burns_filter(w: int, h: int, fps: int, duration: float) -> str:
    """Zoom lent sur une image fixe (Ken Burns) : évite l'effet diaporama.

    On travaille sur une base agrandie pour que le zoom reste net, puis on sort
    directement au format cible."""
    frames = max(1, int(round(duration * fps)))
    big_w, big_h = w * 2, h * 2
    return (
        f"scale={big_w}:{big_h}:force_original_aspect_ratio=decrease,"
        f"pad={big_w}:{big_h}:(ow-iw)/2:(oh-ih)/2,"
        f"zoompan=z='min(zoom+0.0012,1.12)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={w}x{h}:fps={fps}"
    )


async def normalize_photo(src: Path, out: Path, *, w: int, h: int, fps: int,
                          duration: float, ken_burns: bool = False,
                          fade: bool = False) -> Path:
    """Transforme une photo en plan vidéo de `duration` secondes.

    La durée est bornée par un nombre d'images exact (`-frames:v`) plutôt que
    par `-t` : avec `zoompan`, qui émet d images pour CHAQUE image reçue, une
    entrée en boucle multiplierait la durée (bug observé : 2 s rendues en 100 s).
    """
    frames = max(1, int(round(duration * fps)))
    vf_tail = ",setsar=1,format=yuv420p" + (",fade=t=in:st=0:d=0.4" if fade else "")

    if ken_burns:
        # Une seule image en entrée : zoompan produit exactement `frames` images.
        vf = _ken_burns_filter(w, h, fps, duration) + vf_tail
        await _run("ffmpeg", "-y", "-i", str(src), "-vf", vf,
                   "-frames:v", str(frames), "-r", str(fps), *_ENC, str(out))
    else:
        vf = f"{_fit_filter(w, h)},fps={fps}" + vf_tail
        await _run("ffmpeg", "-y", "-loop", "1", "-i", str(src), "-vf", vf,
                   "-frames:v", str(frames), "-r", str(fps), *_ENC, str(out))
    return out


async def normalize_video(src: Path, out: Path, *, w: int, h: int, fps: int,
                          duration: float, in_point: float = 0.0,
                          fade: bool = False) -> Path:
    """Découpe un extrait d'une vidéo et le normalise au format cible."""
    vf = f"{_fit_filter(w, h)},fps={fps},setsar=1,format=yuv420p"
    if fade:
        vf += ",fade=t=in:st=0:d=0.4"
    cmd = ["ffmpeg", "-y"]
    if in_point > 0:
        cmd += ["-ss", f"{in_point:.3f}"]          # seek avant -i : rapide
    cmd += ["-i", str(src), "-t", f"{duration:.3f}",
            "-vf", vf, "-r", str(fps), *_ENC, str(out)]
    await _run(*cmd)
    return out


_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)


def _font_file() -> str | None:
    for f in _FONTS:
        if Path(f).exists():
            return f
    return None


def _esc_drawtext(text: str) -> str:
    """Échappe le texte pour le filtre drawtext (\\ : ' %)."""
    out = text.replace("\\", "\\\\").replace(":", "\\:")
    out = out.replace("'", "\\'").replace("%", "\\%")
    return out


async def burn_watermark(src: Path, out: Path, text: str, *, height: int) -> Path:
    """Incruste le filigrane dans l'image (non retirable après coup).

    Décidé côté serveur selon le rôle : un utilisateur gratuit ne peut pas
    l'enlever, puisqu'il est gravé dans les pixels au rendu."""
    font = _font_file()
    size = max(14, int(height / 40))          # discret mais lisible
    draw = (f"drawtext=text='{_esc_drawtext(text)}':"
            f"fontcolor=white@0.72:fontsize={size}:"
            f"box=1:boxcolor=black@0.22:boxborderw={max(5, size // 3)}:"
            f"x=w-tw-{size}:y=h-th-{size}")
    if font:
        draw = f"drawtext=fontfile={font}:" + draw[len("drawtext="):]
    await _run("ffmpeg", "-y", "-i", str(src), "-vf", draw,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
               str(out))
    return out


async def concat(parts: list[Path], out: Path) -> Path:
    """Assemble les plans normalisés (démuxeur concat, sans ré-encodage)."""
    if not parts:
        raise ValueError("Aucun plan à assembler.")
    listing = out.parent / f"{out.stem}.concat.txt"
    # Le démuxeur concat attend des chemins entre apostrophes, apostrophes échappées.
    listing.write_text(
        "".join(f"file '{str(p).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n"
                for p in parts),
        encoding="utf-8",
    )
    try:
        await _run("ffmpeg", "-y", "-f", "concat", "-safe", "0",
                   "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out))
    finally:
        listing.unlink(missing_ok=True)
    return out
