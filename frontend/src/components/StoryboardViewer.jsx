import { useState } from "react";
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

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      setSb(await api.storyboard(brief));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
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
          <p className="muted small-text">
            Prochaine étape (Slice 3) : ce storyboard alimente le rendu Remotion → MP4 vertical.
          </p>
        </>
      )}
    </div>
  );
}
