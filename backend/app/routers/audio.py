"""Routes du module audio toolkit."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..audio.schema import AudioClip, AudioJob, AudioJobStatus
from ..audio.service import (
    demucs_available,
    extract_from_video,
    import_audio,
    run_apply_job,
    run_separate_job,
)
from ..audio.service import _resolve_video_source
from ..audio.storage import (
    delete_clip,
    get_clip,
    get_job,
    list_clips,
    save_job,
    video_dir,
)

router = APIRouter(prefix="/api/audio")

_MAX_UPLOAD = 200 * 1024 * 1024  # 200 Mo


class ToolkitInfo(BaseModel):
    demucs_available: bool
    max_upload_mb: int


@router.get("/info", response_model=ToolkitInfo)
async def info() -> ToolkitInfo:
    return ToolkitInfo(demucs_available=demucs_available(), max_upload_mb=200)


@router.get("/library", response_model=list[AudioClip])
async def library() -> list[AudioClip]:
    return list_clips()


@router.get("/clips/{clip_id}", response_model=AudioClip)
async def clip_detail(clip_id: str) -> AudioClip:
    c = get_clip(clip_id)
    if c is None:
        raise HTTPException(404, "Clip introuvable.")
    return c


@router.delete("/clips/{clip_id}")
async def clip_delete(clip_id: str) -> dict:
    if not delete_clip(clip_id):
        raise HTTPException(404, "Clip introuvable.")
    return {"status": "deleted"}


@router.post("/upload-video", response_model=AudioClip)
async def upload_video(
    file: UploadFile = File(...),
    name: str | None = Form(None),
) -> AudioClip:
    """Upload une vidéo, extrait sa piste audio, la met en bibliothèque.

    La vidéo source est conservée (elle peut être remuxée plus tard)."""
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide.")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(413, "Fichier trop volumineux (max 200 Mo).")
    video_id = uuid4().hex
    vpath = video_dir() / f"{video_id}.mp4"
    vpath.write_bytes(data)
    try:
        clip = await extract_from_video(vpath, name or (file.filename or "vidéo"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, str(exc)) from exc
    # On rattache l'id de la vidéo sur le clip pour permettre le remux ensuite.
    clip.source_video_name = f"{video_id}.mp4"
    return clip


@router.post("/upload-audio", response_model=AudioClip)
async def upload_audio(
    file: UploadFile = File(...),
    name: str | None = Form(None),
) -> AudioClip:
    """Upload direct d'un fichier audio (mp3, wav, m4a…)."""
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide.")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(413, "Fichier trop volumineux (max 200 Mo).")
    tmp = video_dir() / f"_up_{uuid4().hex}"
    tmp.write_bytes(data)
    try:
        clip = await import_audio(tmp, name or (file.filename or "audio"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, str(exc)) from exc
    finally:
        tmp.unlink(missing_ok=True)
    return clip


@router.post("/clips/{clip_id}/separate", response_model=AudioJob)
async def separate(clip_id: str, background: BackgroundTasks) -> AudioJob:
    """Lance la séparation voix/musique (asynchrone)."""
    clip = get_clip(clip_id)
    if clip is None:
        raise HTTPException(404, "Clip introuvable.")
    if not demucs_available():
        raise HTTPException(
            503,
            "Demucs n'est pas installé sur ce serveur. `pip install demucs`.",
        )
    job = AudioJob(kind="separate", status=AudioJobStatus.QUEUED, input_clip_id=clip_id)
    save_job(job)
    background.add_task(run_separate_job, job.id)
    return job


class ApplyRequest(BaseModel):
    #: id de la vidéo source (celle uploadée via /upload-video)
    video_source_id: str
    #: clip audio à appliquer (None = SUPPRIMER l'audio)
    audio_clip_id: str | None = None
    #: True = mixer par-dessus l'original, False = remplacer
    mix_with_original: bool = False


@router.post("/apply", response_model=AudioJob)
async def apply(req: ApplyRequest, background: BackgroundTasks) -> AudioJob:
    """Applique un clip audio à une vidéo source (asynchrone)."""
    if _resolve_video_source(req.video_source_id) is None:
        raise HTTPException(404, "Vidéo source introuvable.")
    if req.audio_clip_id and get_clip(req.audio_clip_id) is None:
        raise HTTPException(404, "Clip audio introuvable.")
    job = AudioJob(kind="apply", input_clip_id=req.audio_clip_id)
    save_job(job)
    background.add_task(
        run_apply_job, job.id, req.video_source_id, req.audio_clip_id, req.mix_with_original,
    )
    return job


@router.get("/jobs/{job_id}", response_model=AudioJob)
async def job_detail(job_id: str) -> AudioJob:
    j = get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job introuvable.")
    return j
