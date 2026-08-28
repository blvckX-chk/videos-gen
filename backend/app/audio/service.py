"""Opérations audio : extract / separate / remux.

Toutes les étapes lourdes sont exécutées via subprocess (ffmpeg pour l'IO
audio-vidéo, `python -m demucs` pour la séparation voix/musique). C'est
volontaire : ça isole les dépendances lourdes (torch) et permet de tomber
proprement si Demucs n'est pas installé, sans casser le reste du module.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from .schema import AudioClip, AudioJob, AudioJobStatus, ClipKind
from .storage import (
    audio_dir,
    clip_path,
    get_clip,
    get_job,
    probe_audio,
    save_clip,
    save_job,
    video_dir,
)

logger = logging.getLogger("videos_gen.audio")


def demucs_available() -> bool:
    """Vrai si le CLI Demucs est utilisable dans le venv courant."""
    try:
        import demucs  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Utilitaires ffmpeg
# --------------------------------------------------------------------------- #
async def _run(*cmd: str) -> tuple[int, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out or b""


def _fill_clip_meta(clip: AudioClip, path: Path) -> AudioClip:
    info = probe_audio(path)
    clip.duration_seconds = round(info["duration"], 2)
    clip.sample_rate = info["sample_rate"]
    clip.channels = info["channels"]
    clip.size_bytes = info["size"]
    return clip


# --------------------------------------------------------------------------- #
# 1) Extraction audio depuis une vidéo (ou upload direct d'un audio)
# --------------------------------------------------------------------------- #
async def extract_from_video(source_path: Path, name: str) -> AudioClip:
    """Extrait la première piste audio → MP3 128 kbps stéréo."""
    clip = AudioClip(name=name, kind=ClipKind.ORIGINAL,
                     url="", source_video_name=source_path.name)
    out = clip_path(clip.id, "mp3")
    code, log = await _run(
        "ffmpeg", "-y", "-i", str(source_path),
        "-vn", "-ac", "2", "-ar", "44100", "-b:a", "128k", str(out),
    )
    if code != 0 or not out.exists():
        raise RuntimeError(f"ffmpeg extract a échoué : {log[-400:].decode(errors='replace')}")
    clip.url = f"/audio/{out.name}"
    return save_clip(_fill_clip_meta(clip, out))


async def import_audio(source_path: Path, name: str) -> AudioClip:
    """Ré-encode un fichier audio uploadé en MP3 normalisé."""
    clip = AudioClip(name=name, kind=ClipKind.CUSTOM, url="")
    out = clip_path(clip.id, "mp3")
    code, log = await _run(
        "ffmpeg", "-y", "-i", str(source_path),
        "-ac", "2", "-ar", "44100", "-b:a", "128k", str(out),
    )
    if code != 0 or not out.exists():
        raise RuntimeError(f"ffmpeg import a échoué : {log[-400:].decode(errors='replace')}")
    clip.url = f"/audio/{out.name}"
    return save_clip(_fill_clip_meta(clip, out))


# --------------------------------------------------------------------------- #
# 2) Séparation voix / musique (Demucs)
# --------------------------------------------------------------------------- #
async def separate_clip(clip: AudioClip) -> tuple[AudioClip, AudioClip]:
    """Sépare un clip en (vocals, instrumental) via Demucs (modèle htdemucs).

    On utilise le CLI `python -m demucs` pour isoler la dépendance à torch.
    Le modèle est téléchargé au premier appel (~80 Mo dans `~/.cache/torch`
    depuis `dl.fbaipublicfiles.com`). Sur une infra à sortie réseau restreinte,
    pré-télécharger le modèle et le placer dans le cache pour éviter l'appel.
    """
    if not demucs_available():
        raise RuntimeError(
            "Demucs n'est pas installé. `pip install demucs` (attention : "
            "installe PyTorch, ~2 Go)."
        )

    src = clip_path(clip.id, "mp3")
    if not src.exists():
        raise RuntimeError("Fichier audio source introuvable.")

    work = audio_dir() / f"_sep_{clip.id}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    # --two-stems=vocals ⇒ produit `vocals.wav` et `no_vocals.wav`.
    code, log = await _run(
        "python", "-m", "demucs", "--two-stems=vocals",
        "-n", "htdemucs", "-o", str(work), str(src),
    )
    if code != 0:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(f"Demucs a échoué : {log[-400:].decode(errors='replace')}")

    # Retrouve les stems (chemin : <work>/htdemucs/<stem>/<vocals|no_vocals>.wav)
    stems_root = next((p for p in work.rglob("vocals.wav")), None)
    if stems_root is None:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError("Demucs : sortie 'vocals.wav' introuvable.")
    stem_dir = stems_root.parent

    async def _finalize(stem_wav: Path, kind: ClipKind, label: str) -> AudioClip:
        out_clip = AudioClip(
            name=f"{clip.name} — {label}", kind=kind, parent_id=clip.id, url="",
            source_video_name=clip.source_video_name,
        )
        out_mp3 = clip_path(out_clip.id, "mp3")
        code2, log2 = await _run(
            "ffmpeg", "-y", "-i", str(stem_wav),
            "-ac", "2", "-ar", "44100", "-b:a", "160k", str(out_mp3),
        )
        if code2 != 0 or not out_mp3.exists():
            raise RuntimeError(f"ré-encodage stem a échoué : {log2[-400:].decode(errors='replace')}")
        out_clip.url = f"/audio/{out_mp3.name}"
        return save_clip(_fill_clip_meta(out_clip, out_mp3))

    vocals = await _finalize(stem_dir / "vocals.wav", ClipKind.VOCALS, "voix")
    instrumental = await _finalize(stem_dir / "no_vocals.wav", ClipKind.INSTRUMENTAL, "musique")
    shutil.rmtree(work, ignore_errors=True)
    return vocals, instrumental


# --------------------------------------------------------------------------- #
# 3) Remux : appliquer un audio à une vidéo (remplacer / mixer / supprimer)
# --------------------------------------------------------------------------- #
async def apply_audio_to_video(
    video_path: Path,
    audio_path: Path | None,
    out_path: Path,
    mix_with_original: bool = False,
    original_volume: float = 0.15,
    audio_volume: float = 1.0,
) -> Path:
    """Écrit un MP4 :
       - `audio_path=None` → piste audio SUPPRIMÉE
       - `mix_with_original=False` → l'audio REMPLACE la piste d'origine
       - `mix_with_original=True` → l'audio est MIXÉ par-dessus l'original."""
    if audio_path is None:
        code, log = await _run(
            "ffmpeg", "-y", "-i", str(video_path), "-c:v", "copy", "-an", str(out_path),
        )
    elif not mix_with_original:
        code, log = await _run(
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_path),
        )
    else:
        # Ducking simple : baisse l'original, superpose l'audio à plein.
        filt = (
            f"[0:a]volume={original_volume}[a0];"
            f"[1:a]volume={audio_volume}[a1];"
            "[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        )
        code, log = await _run(
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
            "-filter_complex", filt, "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out_path),
        )
    if code != 0 or not out_path.exists():
        raise RuntimeError(f"ffmpeg remux a échoué : {log[-400:].decode(errors='replace')}")
    return out_path


# --------------------------------------------------------------------------- #
# Runners de job (arrière-plan)
# --------------------------------------------------------------------------- #
async def run_separate_job(job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = AudioJobStatus.RUNNING
        job.touch()
        clip = get_clip(job.input_clip_id or "")
        if clip is None:
            raise RuntimeError("Clip introuvable.")
        voc, instr = await separate_clip(clip)
        job.output_clip_ids = [voc.id, instr.id]
        job.status = AudioJobStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.exception("séparation %s échouée", job_id)
        job.status = AudioJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)


def _resolve_video_source(video_id: str) -> tuple[Path, str] | None:
    """Un même id peut désigner une vidéo uploadée (`audio_sources/`) ou un
    rendu Remotion (`renders/`). Renvoie (path, kind) ou None."""
    from ..render.service import storage_root
    candidates = [
        (video_dir() / f"{video_id}.mp4", "audio_sources"),
        (storage_root() / "renders" / f"{video_id}.mp4", "renders"),
    ]
    for p, kind in candidates:
        if p.exists():
            return p, kind
    return None


async def run_apply_job(job_id: str, video_id: str, audio_clip_id: str | None,
                         mix: bool = False) -> None:
    job = get_job(job_id)
    if job is None:
        return
    try:
        job.status = AudioJobStatus.RUNNING
        job.touch()

        found = _resolve_video_source(video_id)
        if not found:
            raise RuntimeError("Vidéo source introuvable.")
        video_path, _ = found

        audio_path: Path | None = None
        if audio_clip_id:
            clip = get_clip(audio_clip_id)
            if clip is None:
                raise RuntimeError("Clip audio cible introuvable.")
            audio_path = clip_path(clip.id, "mp3")

        out = video_dir() / f"{video_id}_remixed_{job.id}.mp4"
        await apply_audio_to_video(video_path, audio_path, out, mix_with_original=mix)
        job.output_video_url = f"/audio_sources/{out.name}"
        job.status = AudioJobStatus.SUCCEEDED
    except Exception as exc:  # noqa: BLE001
        logger.exception("remux %s échoué", job_id)
        job.status = AudioJobStatus.FAILED
        job.error = str(exc)
    finally:
        job.touch()
        save_job(job)
