"""Storage sur disque + registre en mémoire des clips audio et jobs.

Les fichiers audio vivent dans `storage/audio/<clip_id>.<ext>` — servis via
la route statique `/audio/*` montée dans `main.py`.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .. import db
from ..render.service import storage_root
from .schema import AudioClip, AudioJob

logger = logging.getLogger("videos_gen.audio")

_CLIPS_COLLECTION = "audio_clips"
_JOBS_COLLECTION = "audio_jobs"
_CLIPS: dict[str, AudioClip] = {}
_JOBS: dict[str, AudioJob] = {}


def audio_dir() -> Path:
    d = storage_root() / "audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def video_dir() -> Path:
    """Vidéos sources uploadées (pour remuxer plus tard)."""
    d = storage_root() / "audio_sources"
    d.mkdir(parents=True, exist_ok=True)
    return d


def clip_path(clip_id: str, ext: str = "mp3") -> Path:
    return audio_dir() / f"{clip_id}.{ext}"


def probe_audio(path: Path) -> dict:
    """Renvoie {duration, sample_rate, channels, size} via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels:format=duration",
         "-of", "default=nw=1", str(path)],
        capture_output=True, text=True, check=False,
    )
    info = {"duration": 0.0, "sample_rate": 44100, "channels": 2, "size": path.stat().st_size}
    for line in r.stdout.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k == "duration":
            info["duration"] = float(v or 0)
        elif k == "sample_rate":
            info["sample_rate"] = int(v or 44100)
        elif k == "channels":
            info["channels"] = int(v or 2)
    return info


def save_clip(clip: AudioClip) -> AudioClip:
    _CLIPS[clip.id] = clip
    db.put(_CLIPS_COLLECTION, clip.id, clip.model_dump(mode="json"))
    return clip


def get_clip(clip_id: str) -> AudioClip | None:
    return _CLIPS.get(clip_id)


def list_clips() -> list[AudioClip]:
    return sorted(_CLIPS.values(), key=lambda c: c.created_at, reverse=True)


def delete_clip(clip_id: str) -> bool:
    clip = _CLIPS.pop(clip_id, None)
    if clip is None:
        return False
    db.delete(_CLIPS_COLLECTION, clip_id)
    for ext in ("mp3", "wav", "m4a"):
        p = clip_path(clip_id, ext)
        if p.exists():
            p.unlink()
    return True


def save_job(job: AudioJob) -> AudioJob:
    _JOBS[job.id] = job
    db.put(_JOBS_COLLECTION, job.id, job.model_dump(mode="json"))
    return job


def get_job(job_id: str) -> AudioJob | None:
    return _JOBS.get(job_id)


def rehydrate() -> int:
    """Recharge clips + jobs audio depuis la base (au démarrage)."""
    _CLIPS.clear()
    _JOBS.clear()
    for data in db.all(_CLIPS_COLLECTION):
        try:
            c = AudioClip.model_validate(data)
            _CLIPS[c.id] = c
        except Exception:  # noqa: BLE001
            logger.warning("Clip audio illisible ignoré", exc_info=True)
    for data in db.all(_JOBS_COLLECTION):
        try:
            j = AudioJob.model_validate(data)
            _JOBS[j.id] = j
        except Exception:  # noqa: BLE001
            logger.warning("Job audio illisible ignoré", exc_info=True)
    return len(_CLIPS) + len(_JOBS)
