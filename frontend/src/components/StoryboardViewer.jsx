import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import AudioLibrary from "./AudioLibrary.jsx";

const SHOT_LABEL = {
  title: "Titre",
  text: "Texte",
  page: "Page",
  panel: "Case",
  stat: "Chiffre",
  quote: "Citation",
  outro: "Outro",
  broll: "B-roll",
};

// Timeline du storyboard : scènes → shots, avec durée cumulée.
export default function StoryboardViewer({ brief }) {
  const [sb, setSb] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [renderJob, setRenderJob] = useState(null);
  const [rendering, setRendering] = useState(false);
  const [tier, setTier] = useState("free");
  // Slice 4 — post-production
  const [narration, setNarration] = useState(true);
  const [captions, setCaptions] = useState(true);
  const [voiceProvider, setVoiceProvider] = useState("");
  const [voices, setVoices] = useState([]);
  const [musicClip, setMusicClip] = useState(null);
  const poller = useRef(null);

  useEffect(() => { api.voices().then(setVoices).catch(() => {}); }, []);
  // Post-rendu : coller une piste audio de la bibliothèque au MP4 obtenu.
  const [pickedAudio, setPickedAudio] = useState(null);
  const [mixMode, setMixMode] = useState(false);
  const [audioJob, setAudioJob] = useState(null);
  const audioPoller = useRef(null);
  useEffect(() => () => audioPoller.current && clearInterval(audioPoller.current), []);

  useEffect(() => () => poller.current && clearInterval(poller.current), []);

  async function generate() {
    setLoading(true);
    setError(null);
    setRenderJob(null);
    try {
      setSb(await api.storyboard(brief));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function renderVideo() {
    if (!sb) return;
    setError(null);
    setRendering(true);
    try {
      const j = await api.render(sb, {
        tier,
        narration,
        captions,
        voice_provider: voiceProvider || null,
        music_clip_id: musicClip || null,
      });
      setRenderJob(j);
      poller.current && clearInterval(poller.current);
      poller.current = setInterval(async () => {
        try {
          const upd = await api.renderStatus(j.id);
          setRenderJob(upd);
          if (upd.status === "succeeded" || upd.status === "failed") {
            clearInterval(poller.current);
            setRendering(false);
          }
        } catch {
          clearInterval(poller.current);
          setRendering(false);
        }
      }, 2500);
    } catch (e) {
      setError(e.message);
      setRendering(false);
    }
  }

  const total = sb
    ? sb.scenes.reduce((a, sc) => a + sc.shots.reduce((b, s) => b + s.duration, 0), 0)
    : 0;

  return (
    <div className="storyboard">
      {!sb && (
        <button className="primary" onClick={generate} disabled={loading}>
          {loading ? "Génération du storyboard…" : "🎬 Générer le storyboard"}
        </button>
      )}
      {error && <div className="banner error" style={{ marginTop: 12 }}>{error}</div>}

      {sb && (
        <>
          <div className="sb-meta">
            <span className="pill p-p1">{sb.template}</span>
            <span>{sb.generator === "rule_based" ? "règle-based" : sb.generator}</span>
            <span><b>{Math.round(total)}s</b> · {sb.scenes.reduce((a, s) => a + s.shots.length, 0)} shots</span>
            <span className="formats">{sb.formats.map((f) => <em key={f}>{f}</em>)}</span>
            <button className="ghost small" onClick={generate} disabled={loading}>Régénérer</button>
          </div>

          <div className="timeline">
            {sb.scenes.map((sc) => (
              <div key={sc.index} className="sb-scene">
                <div className="sb-scene-title">{sc.title || `Scène ${sc.index + 1}`}</div>
                <div className="sb-shots">
                  {sc.shots.map((s) => (
                    <div key={s.index} className={`sb-shot t-${s.type}`} style={{ flexGrow: s.duration }}>
                      <span className="sb-type">{SHOT_LABEL[s.type] || s.type}</span>
                      {s.text && <span className="sb-text">{s.text}</span>}
                      {s.source_panel != null && (
                        <span className="sb-src">p{s.source_page + 1}·c{s.source_panel + 1}</span>
                      )}
                      {s.source_panel == null && s.source_page != null && (
                        <span className="sb-src">p{s.source_page + 1}</span>
                      )}
                      <span className="sb-dur">{s.duration}s</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="render-block">
            <h4>Rendu vidéo</h4>

            <div className="render-audio-opts">
              <label className="checkbox-line">
                <input type="checkbox" checked={narration}
                  onChange={(e) => setNarration(e.target.checked)} disabled={rendering} />
                <span>Voix off</span>
              </label>
              <label className="checkbox-line">
                <input type="checkbox" checked={captions}
                  onChange={(e) => setCaptions(e.target.checked)} disabled={rendering} />
                <span>Sous-titres</span>
              </label>
              <label className="field small">
                <span>Voix</span>
                <select value={voiceProvider} onChange={(e) => setVoiceProvider(e.target.value)}
                  disabled={rendering || !narration}>
                  <option value="">auto (gratuit)</option>
                  {voices.filter((v) => v.available).map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}{v.free ? "" : " · premium"}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {sb && (
              <details className="music-picker">
                <summary>Musique de fond (optionnel)</summary>
                <p className="muted small-text">Choisis une piste de la bibliothèque audio (atténuée sous la voix).</p>
                <AudioLibrary mode="picker" selectedId={musicClip} onSelect={setMusicClip} />
              </details>
            )}

            <div className="render-controls">
              <div className="tier-toggle">
                <button
                  className={`chip ${tier === "free" ? "active" : ""}`}
                  onClick={() => setTier("free")}
                  disabled={rendering}
                >
                  Free · gratuit
                </button>
                <button
                  className={`chip ${tier === "premium" ? "active" : ""}`}
                  onClick={() => setTier("premium")}
                  disabled={rendering}
                  title="Active les providers payants (Slice 4+)"
                >
                  Premium
                </button>
              </div>
              <button
                className="primary"
                onClick={renderVideo}
                disabled={rendering || (renderJob && renderJob.status === "running")}
              >
                {rendering ? "Rendu en cours…" : "🎥 Rendre la vidéo"}
              </button>
            </div>

            {renderJob && (
              <div className="render-status">
                <span className={`badge ${renderJob.status}`}>{renderJob.status}</span>
                {renderJob.tier && <span className="muted"> · tier <b>{renderJob.tier}</b></span>}
                {renderJob.costs?.length > 0 && (
                  <span className="muted">
                    {" "}· coût <b>{renderJob.costs.reduce((a, c) => a + (c.cost_cents || 0), 0)}¢</b>
                  </span>
                )}
                {renderJob.status === "failed" && (
                  <div className="banner error" style={{ marginTop: 10 }}>{renderJob.error}</div>
                )}
                {renderJob.status === "succeeded" && renderJob.video_url && (
                  <div className="render-player">
                    <video src={renderJob.video_url} controls playsInline />
                    <a href={renderJob.video_url} download className="ghost small">
                      Télécharger le MP4
                    </a>

                    <div className="post-audio">
                      <h4>Ajouter une piste audio</h4>
                      <p className="muted small-text">
                        Choisis un clip depuis l'onglet Audio toolkit, ou laisse
                        <b> Aucun audio</b> pour un MP4 muet.
                      </p>
                      <AudioLibrary
                        mode="picker"
                        selectedId={pickedAudio}
                        onSelect={setPickedAudio}
                      />
                      <label className="checkbox-line">
                        <input
                          type="checkbox"
                          checked={mixMode}
                          onChange={(e) => setMixMode(e.target.checked)}
                        />
                        <span>Mixer par-dessus l'original (sinon : remplace)</span>
                      </label>
                      <button
                        className="primary"
                        disabled={audioJob && audioJob.status === "running"}
                        onClick={async () => {
                          try {
                            const videoId = renderJob.video_url
                              .replace("/renders/", "")
                              .replace(".mp4", "");
                            const j = await api.audio.apply({
                              video_source_id: videoId,
                              audio_clip_id: pickedAudio,
                              mix_with_original: mixMode,
                            });
                            setAudioJob(j);
                            audioPoller.current && clearInterval(audioPoller.current);
                            audioPoller.current = setInterval(async () => {
                              const upd = await api.audio.job(j.id);
                              setAudioJob(upd);
                              if (upd.status === "succeeded" || upd.status === "failed")
                                clearInterval(audioPoller.current);
                            }, 1500);
                          } catch (e) { setError(e.message); }
                        }}
                      >
                        🎧 Appliquer au MP4
                      </button>
                      {audioJob && (
                        <div className="apply-result">
                          <p className="muted small-text">
                            Rendu audio : <b>{audioJob.status}</b>
                            {audioJob.error && (
                              <span className="err"> — {audioJob.error}</span>
                            )}
                          </p>
                          {audioJob.status === "succeeded" && audioJob.output_video_url && (
                            <>
                              <video
                                src={audioJob.output_video_url}
                                controls
                                playsInline
                                style={{ maxWidth: 320, width: "100%", borderRadius: 12 }}
                              />
                              <a
                                className="ghost small"
                                href={audioJob.output_video_url}
                                download
                              >
                                Télécharger la version avec audio
                              </a>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
