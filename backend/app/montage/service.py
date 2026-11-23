"""Rendu d'une Timeline en MP4.

Chaîne : normalisation de chaque plan → concaténation → post-production
(voix off, musique) → incrustation du filigrane → MP4 final.

La décision de filigrane est prise ici, côté serveur, à partir du rôle déjà
authentifié par le routeur : un rôle gratuit ne peut pas l'éviter.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from ..media import storage as media_store
from ..media.schema import MediaKind
from ..render.assets import storage_root
from . import ffmpeg_ops as ops
from .schema import (FORMAT_DIMS, MontageJob, MontageJobStatus, Timeline,
                     Transition, TransitionStyle)
from .storage import save_job

logger = logging.getLogger("videos_gen.montage")


def _renders_dir() -> Path:
    d = storage_root() / "renders"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _work_dir(job_id: str) -> Path:
    d = storage_root() / "montage_tmp" / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _watermark_for(timeline: Timeline) -> str | None:
    """Texte du filigrane, ou None si le rôle autorise son retrait."""
    from ..identity.entitlements import decide_watermark, get_entitlements
    from ..identity.schema import Role

    try:
        role = Role(timeline.role) if timeline.role else Role.FREE
    except ValueError:
        role = Role.FREE                      # rôle inconnu → défaut sûr
    ent = get_entitlements(role)

    text = timeline.watermark_text
    if timeline.charte_id:
        from ..identity.charters import get_charte
        charte = get_charte(timeline.charte_id)
        if charte is not None and charte.watermark_text:
            text = text or charte.watermark_text

    show, resolved = decide_watermark(ent, timeline.remove_watermark, text)
    return (resolved or "blvckUnlimited") if show else None


async def _synthesize_narration(text: str, out: Path) -> Path | None:
    """Voix off avec le meilleur provider gratuit disponible (Piper en tête)."""
    try:
        from ..voice.providers.registry import default_free_tts
        provider = default_free_tts()
        return await provider.synthesize(text, out, lang="fr")
    except Exception:  # noqa: BLE001 — la narration est un bonus, pas un bloquant
        logger.warning("Narration ignorée (aucun TTS disponible)", exc_info=True)
        return None


async def run_montage(job: MontageJob, timeline: Timeline) -> None:
    """Exécute le montage. Met le job à jour à chaque étape (suivi côté UI)."""
    work = _work_dir(job.id)
    try:
        if not timeline.clips:
            raise ValueError("La timeline ne contient aucun plan.")

        job.status = MontageJobStatus.RUNNING
        job.clips_total = len(timeline.clips)
        job.clips_done = 0
        job.step = "Préparation des plans"
        job.touch(); save_job(job)

        w, h = FORMAT_DIMS[timeline.format]
        fps = timeline.fps
        fit = timeline.fit_mode.value

        # 1) Normaliser chaque plan : même vidéo ET même audio (sinon l'assemblage
        #    de sources hétérogènes casse). Le son des rushes est conservé.
        parts: list[Path] = []
        durations: list[float] = []
        for i, clip in enumerate(timeline.clips):
            media = media_store.get(clip.media_id)
            if media is None:
                raise ValueError(f"Média introuvable pour le plan {i + 1}.")
            src = media_store.media_path(media.id, media.ext)
            if not src.exists():
                raise ValueError(f"Fichier manquant pour le plan {i + 1}.")

            part = work / f"{i:04d}.mp4"
            # Le fondu d'ouverture n'a de sens que sur le premier plan ; entre
            # deux plans, c'est le fondu enchaîné qui s'en charge.
            fade_in = clip.transition == Transition.FADE and i == 0
            if media.kind == MediaKind.PHOTO:
                await ops.normalize_photo(src, part, w=w, h=h, fps=fps,
                                          duration=clip.duration,
                                          ken_burns=clip.ken_burns,
                                          fade_in=fade_in, fit=fit, text=clip.text)
            elif media.kind == MediaKind.VIDEO:
                await ops.normalize_video(src, part, w=w, h=h, fps=fps,
                                          duration=clip.duration,
                                          in_point=clip.in_point,
                                          fade_in=fade_in, fit=fit, text=clip.text)
            else:
                raise ValueError(f"Le plan {i + 1} n'est ni une photo ni une vidéo.")
            parts.append(part)
            durations.append(clip.duration)

            job.clips_done = i + 1
            job.step = f"Plan {i + 1}/{len(timeline.clips)}"
            job.touch(); save_job(job)

        # 2) Assembler — fondus enchaînés ou coupes franches
        dissolve = timeline.transition_style == TransitionStyle.DISSOLVE
        job.step = "Fondus enchaînés" if dissolve else "Assemblage"
        job.touch(); save_job(job)
        bed = work / "bed.mp4"
        if dissolve and len(parts) > 1:
            await ops.concat_dissolve(parts, durations, bed, fps=fps)
        else:
            await ops.concat_cut(parts, bed)

        # 3) Piste son : son d'origine + voix off + musique, normalisé
        voice_path = None
        if timeline.narration:
            job.step = "Voix off"; job.touch(); save_job(job)
            voice_path = await _synthesize_narration(timeline.narration, work / "voice.wav")

        music_path = None
        if timeline.music_media_id:
            m = media_store.get(timeline.music_media_id)
            if m is not None:
                p = media_store.media_path(m.id, m.ext)
                music_path = p if p.exists() else None

        # Toujours mixer : même sans voix ni musique, on normalise le loudness.
        job.step = "Mixage audio"; job.touch(); save_job(job)
        current = work / "mixed.mp4"
        await ops.mix_tracks(bed, current, voice=voice_path, music=music_path)

        # 4) Filigrane (gravé dans l'image, selon le rôle)
        wm = _watermark_for(timeline)
        if wm:
            job.step = "Filigrane"; job.touch(); save_job(job)
            marked = work / "marked.mp4"
            await ops.burn_watermark(current, marked, wm, height=h)
            current = marked

        # 5) Livrer
        final = _renders_dir() / f"{job.id}.mp4"
        shutil.move(str(current), str(final))
        job.video_url = f"/renders/{final.name}"
        job.status = MontageJobStatus.SUCCEEDED
        job.step = "Terminé"
        job.touch(); save_job(job)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Montage %s échoué", job.id)
        job.status = MontageJobStatus.FAILED
        job.error = str(exc)
        job.touch(); save_job(job)
    finally:
        shutil.rmtree(work, ignore_errors=True)
