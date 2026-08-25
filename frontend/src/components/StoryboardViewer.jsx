import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

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
  const poller = useRef(null);

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
      const j = await api.render(sb, tier);
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
