import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import AudioLibrary from "./AudioLibrary.jsx";

// Onglet "Audio toolkit" : upload vidéo/audio, séparation Demucs, remux.
export default function AudioToolkit() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [lastClip, setLastClip] = useState(null);
  const [sepJob, setSepJob] = useState(null);
  const [applyJob, setApplyJob] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [pickedApplyClip, setPickedApplyClip] = useState(null);
  const [mixMode, setMixMode] = useState(false);
  const videoRef = useRef();
  const audioRef = useRef();

  useEffect(() => { api.audio.info().then(setInfo).catch(() => {}); }, []);

  function bump() { setRefreshKey((k) => k + 1); }

  async function handleVideoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setError(null);
    try {
      const clip = await api.audio.uploadVideo(file, file.name);
      setLastClip(clip);
      bump();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); e.target.value = ""; }
  }

  async function handleAudioUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setError(null);
    try {
      const clip = await api.audio.uploadAudio(file, file.name);
      setLastClip(clip);
      bump();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); e.target.value = ""; }
  }

  function pollJob(jobId, setter, onDone) {
    const t = setInterval(async () => {
      try {
        const j = await api.audio.job(jobId);
        setter(j);
        if (j.status === "succeeded" || j.status === "failed") {
          clearInterval(t);
          onDone?.(j);
        }
      } catch { clearInterval(t); }
    }, 2000);
  }

  async function separateLastClip() {
    if (!lastClip) return;
    setError(null);
    try {
      const j = await api.audio.separate(lastClip.id);
      setSepJob(j);
      pollJob(j.id, setSepJob, () => bump());
    } catch (err) { setError(err.message); }
  }

  async function applyToLastVideo() {
    if (!lastClip?.source_video_name) {
      setError("Le clip sélectionné ne provient pas d'une vidéo importée.");
      return;
    }
    const vid = lastClip.source_video_name.replace(".mp4", "");
    try {
      const j = await api.audio.apply({
        video_source_id: vid,
        audio_clip_id: pickedApplyClip,   // null = supprimer l'audio
        mix_with_original: mixMode,
      });
      setApplyJob(j);
      pollJob(j.id, setApplyJob);
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>🎧 Audio toolkit</h2>
      <p className="muted small-text">
        Extraire l'audio d'une vidéo, isoler la voix / la musique (Demucs), coller
        une piste sur une vidéo — le tout tourne 100 % local, tier <code>free</code>.
      </p>

      {info && !info.demucs_available && (
        <div className="banner warn">
          Demucs n'est pas installé — la séparation voix/musique sera indisponible
          tant que <code>pip install demucs</code> n'aura pas été fait sur le serveur.
        </div>
      )}
      {error && <div className="banner error">{error}</div>}

      <div className="uploads">
        <label className="upload">
          <span>📹 Depuis une vidéo</span>
          <input type="file" accept="video/*" ref={videoRef} onChange={handleVideoUpload} disabled={busy} />
          <em>MP4/MOV → extrait l'audio</em>
        </label>
        <label className="upload">
          <span>🎧 Depuis un audio</span>
          <input type="file" accept="audio/*" ref={audioRef} onChange={handleAudioUpload} disabled={busy} />
          <em>MP3/WAV → ajoute à la bibliothèque</em>
        </label>
      </div>

      {lastClip && (
        <div className="last-clip">
          <h3>Dernier import</h3>
          <div className="audio-card">
            <div className="ac-head">
              <b>{lastClip.name}</b>
              <span className="ac-kind">{lastClip.kind} · {lastClip.duration_seconds}s</span>
            </div>
            <audio controls src={lastClip.url} style={{ width: "100%" }} />
          </div>
          <div className="last-actions">
            <button
              className="ghost"
              onClick={separateLastClip}
              disabled={!info?.demucs_available || (sepJob && sepJob.status === "running")}
              title={info?.demucs_available ? "Sépare voix et musique" : "Demucs indisponible"}
            >
              🗣️ / 🎵 Séparer voix &amp; musique
            </button>
          </div>
          {sepJob && (
            <p className="muted small-text">
              Séparation : <b>{sepJob.status}</b>
              {sepJob.error && <span className="err"> — {sepJob.error}</span>}
              {sepJob.status === "succeeded" && " ✓ voir bibliothèque ↓"}
            </p>
          )}
        </div>
      )}

      {lastClip?.source_video_name && (
        <div className="apply-panel">
          <h3>Remux — coller un audio sur cette vidéo</h3>
          <p className="muted small-text">
            Choisis un clip de la bibliothèque à appliquer, ou <b>Aucun audio</b>
            pour simplement supprimer la piste. Le mix garde 15 % du son original.
          </p>
          <AudioLibrary mode="picker" selectedId={pickedApplyClip} onSelect={setPickedApplyClip} refreshKey={refreshKey} />
          <label className="checkbox-line">
            <input type="checkbox" checked={mixMode} onChange={(e) => setMixMode(e.target.checked)} />
            <span>Mixer par-dessus l'original (sinon : remplace)</span>
          </label>
          <button className="primary" onClick={applyToLastVideo} disabled={applyJob && applyJob.status === "running"}>
            🎬 Appliquer
          </button>
          {applyJob && (
            <div className="apply-result">
              <p className="muted small-text">
                Rendu : <b>{applyJob.status}</b>
                {applyJob.error && <span className="err"> — {applyJob.error}</span>}
              </p>
              {applyJob.status === "succeeded" && applyJob.output_video_url && (
                <>
                  <video src={applyJob.output_video_url} controls playsInline style={{ maxWidth: 320, width: "100%", borderRadius: 12 }} />
                  <a className="ghost small" href={applyJob.output_video_url} download>Télécharger</a>
                </>
              )}
            </div>
          )}
        </div>
      )}

      <div className="library-section">
        <h3>Bibliothèque</h3>
        <AudioLibrary mode="manage" refreshKey={refreshKey} />
      </div>
    </div>
  );
}
